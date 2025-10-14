FROM ubuntu:14.04

RUN apt-get update && \
    apt-get install -y build-essential zlib1g-dev wget && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src
RUN wget https://www.openssl.org/source/openssl-1.0.1f.tar.gz
RUN tar -xzvf openssl-1.0.1f.tar.gz
WORKDIR /usr/src/openssl-1.0.1f
RUN ./config --prefix=/usr/local/openssl --openssldir=/usr/local/openssl shared zlib
RUN make
RUN make install_sw
RUN mv /usr/bin/openssl /usr/bin/openssl.bak
RUN ln -s /usr/local/openssl/bin/openssl /usr/bin/openssl
WORKDIR /srv

# Generate 1024-bit self-signed certificate for export cipher testing
RUN mkdir /srv/certs && \
    openssl req -x509 -newkey rsa:1024 \
      -keyout /srv/certs/key.pem \
      -out /srv/certs/cert.pem \
      -days 365 -nodes \
      -subj "/CN=localhost"

EXPOSE 8443

# Copy certs into a shared mount at runtime and start the server
RUN printf '%s\n' "#!/bin/sh" \
    "set -e" \
    "mkdir -p /shared_certs" \
    "cp -f /srv/certs/cert.pem /shared_certs/cert.pem || true" \
    "cp -f /srv/certs/key.pem /shared_certs/key.pem || true" \
    "exec openssl s_server -accept 8443 -cert /srv/certs/cert.pem -key /srv/certs/key.pem -www -cipher 'ALL:EXP'" \
    > /srv/start_server.sh && \
    chmod +x /srv/start_server.sh

CMD ["/srv/start_server.sh"]

