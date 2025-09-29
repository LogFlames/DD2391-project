FROM ubuntu:14.04

RUN apt-get update && \
    apt-get install -y openssl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /srv

# Generate 512-bit self-signed certificate for export cipher testing
RUN mkdir /srv/certs && \
    openssl req -x509 -newkey rsa:512 \
      -keyout /srv/certs/key.pem \
      -out /srv/certs/cert.pem \
      -days 365 -nodes \
      -subj "/CN=localhost"

EXPOSE 8443

# Start OpenSSL s_server with export ciphers enabled
CMD ["openssl", "s_server", "-accept", "8443", "-cert", "/srv/certs/cert.pem", "-key", "/srv/certs/key.pem", "-www", "-cipher", "ALL:EXP", "-tls1"]

