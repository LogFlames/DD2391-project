FROM ubuntu:20.04

# Install dependencies (x11-apps for testing, wget for download, and required libs for old Firefox)
RUN apt-get update && \
    apt-get install -y wget x11-apps libgtk2.0-0 libdbus-glib-1-2 libxt6 libx11-6 libasound2 libcanberra-gtk-module libcanberra-gtk0 libxss1 libnss3 libxcomposite1 libxcursor1 libxdamage1 libxi6 libxtst6 libxrandr2 libxinerama1 libxrender1 libfontconfig1 libglib2.0-0 libpango1.0-0 libxfixes3 && \
    rm -rf /var/lib/apt/lists/*

# Download and install Firefox 34 (2014)
RUN wget -O /tmp/firefox.tar.bz2 "https://ftp.mozilla.org/pub/firefox/releases/34.0/linux-x86_64/en-US/firefox-34.0.tar.bz2" && \
    tar -xjf /tmp/firefox.tar.bz2 -C /opt && \
    ln -s /opt/firefox/firefox /usr/bin/firefox && \
    rm /tmp/firefox.tar.bz2

# Set the display environment variable
ENV DISPLAY=:0

# Run old Firefox by default
CMD ["firefox"]