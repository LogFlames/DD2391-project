FROM python:3.10-slim


# Install system dependencies for tshark (Wireshark CLI)
RUN apt-get update && \
	apt-get install -y tshark && \
	rm -rf /var/lib/apt/lists/*


# Install Python dependencies: scapy with TLS support and cryptography
RUN pip install --no-cache-dir 'scapy[complete]' cryptography pycryptodome tlsmate

# Set up a working directory
WORKDIR /srv


# Expose the proxy port (8080 for example)
EXPOSE 8080


# Copy the custom proxy script into the container
COPY freak_mitm.py /srv/freak_mitm.py
COPY tls_session.py /srv/tls_session.py
COPY ssl2.py /srv/ssl2.py

# Run the custom proxy script by default
CMD ["python3", "/srv/freak_mitm.py"]
