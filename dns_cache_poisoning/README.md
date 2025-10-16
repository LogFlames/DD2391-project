# DNS cache poisoning

## Ways of perfoming MITM attacks

- Malicious (probably public) WiFi with a DHCP server which points to a malicious DNS server
- ARP spoofing
- DNS spoofing (done here)

DNS spoofing can be done in two ways:
* One where you are on the local network. When the attaker sees a DNS request, it can respond with a spoofed response knowing the transaction ID (16-bit) and port (16-bit). 
* The other way is done here. The attacker triggers a DNS request and floods the DNS server with spoofed responses. If the transaction ID and port are guessed correctly before the response comes from the real server, a faulty record is cached on the DNS server. To make this easier we turn of port randomization, meaning the attacker only have to guess the transaction id. We also turn of DNSSEC, a new standard using public key cryptogrophy to ensure records are validated. DNSSEC, although released in 2004, has been slow to roll out and still many DNS-servers do not use it.

## Running

```bash
docker compose build && docker compose up
# A DNS server is now running on 172.18.0.2

docker exec -it dns_cache_poisoning-dns_server-1 bash
# Inside the container
/root/flood.sh
# Press enter until ip of [n].eliaslundell.se shows as 192.168.128.128
```

TODO: Add authority NS/SOA section to response to spoof NS record in cache

Currently, it can only try to spoof once every cache refresh. By spoofing the NS record (which should be able to be done while performing a lookup of a non-existent subdomain) it can take over the entire domain.

## Good links

DNS Cache Poisoning labs:
- https://seedsecuritylabs.org/Labs_16.04/PDF/DNS_Remote.pdf
- https://www.utc.edu/sites/default/files/2021-04/dns.pdf

DNS RFC:
- https://datatracker.ietf.org/doc/html/rfc1035

Building a DNS resolver:
- https://gieseanw.wordpress.com/2010/03/25/building-a-dns-resolver/
