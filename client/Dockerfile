FROM ubuntu:14.04

# Install OpenSSL and basic tools
RUN apt-get update && \
    apt-get install -y openssl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /srv

# Wait for services to be up, then run openssl s_client to mitm:8443 with export ciphers
CMD sleep 10 && openssl version && openssl s_client -connect mitm:8443 -cipher EXP -debug
