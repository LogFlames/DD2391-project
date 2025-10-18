# FROM ubuntu:14.04

# # Install OpenSSL and basic tools
# RUN apt-get update && \
#     apt-get install -y openssl && \
#     rm -rf /var/lib/apt/lists/*

# WORKDIR /srv

# # Wait for services to be up, then run openssl s_client to mitm:8443 with export ciphers
# CMD sleep 10 && openssl version && openssl s_client -connect mitm:8443 -cipher ALL -debug
FROM ubuntu:14.04
RUN apt-get update && apt-get install -y build-essential zlib1g-dev wget ca-certificates tcpdump
WORKDIR /usr/src
RUN wget https://www.openssl.org/source/openssl-1.0.1f.tar.gz
RUN tar -xzvf openssl-1.0.1f.tar.gz
WORKDIR /usr/src/openssl-1.0.1f
RUN ./config --prefix=/usr/local/openssl --openssldir=/usr/local/openssl shared zlib
RUN make
RUN make install_sw
RUN mv /usr/bin/openssl /usr/bin/openssl.bak
RUN ln -s /usr/local/openssl/bin/openssl /usr/bin/openssl
RUN printf '%s\n' "#!/bin/sh" \
	"set -e" \
	"if [ -f /shared_certs/cert.pem ]; then cp /shared_certs/cert.pem /usr/local/share/ca-certificates/freak_server.crt && update-ca-certificates; fi" \
	> /usr/local/bin/start_client.sh && \
	chmod +x /usr/local/bin/start_client.sh
RUN ["/usr/local/bin/start_client.sh"]

CMD openssl version; sleep 5; openssl s_client -connect mitm:8443 -tls1 -no_comp; sleep 15; openssl s_client -connect mitm:8443 -tls1 -no_comp