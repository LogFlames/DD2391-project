FROM ubuntu:24.04

RUN apt-get update && \
    apt-get install -y bind9 bind9utils dnsutils && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY ./named.conf /etc/bind/named.conf
COPY ./named.conf.options /etc/bind/named.conf.options

COPY ./example.com.db /var/cache/bind/example.com.db

COPY ./rndc.key /etc/bind/rndc.key

CMD ["named", "-g", "-c", "/etc/bind/named.conf"]
