FROM ubuntu:24.04

RUN apt-get update && \
    apt-get install -y gcc dnsutils && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY ./flood.c /root/flood.c
RUN gcc /root/flood.c -o /root/flood

COPY ./flood.sh /root/flood.sh
RUN chmod +x /root/flood.sh


CMD ["sleep", "100000"]
