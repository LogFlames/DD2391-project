# FREAK (CVE-2015-0204)

**F**actoring **R**SA **E**xport **K**eys

> FREAK ("Factoring RSA Export Keys") is a security exploit of a cryptographic weakness in the SSL/TLS protocols introduced decades earlier for compliance with U.S. cryptography export regulations. These involved limiting exportable software to use only public key pairs with RSA moduli of 512 bits or fewer (so-called RSA EXPORT keys), with the intention of allowing them to be broken easily by the National Security Agency (NSA), but not by other organizations with lesser computing resources. However, by the early 2010s, increases in computing power meant that they could be broken by anyone with access to relatively modest computing resources using the well-known Number Field Sieve algorithm, using as little as $100 of cloud computing services.
> 
> *en.wikipedia.org/wiki/FREAK, 18 sept 2025*

## Table of Contents

[**FREAK (CVE-2015-0204)**](#freak-cve-2015-0204)

0. [**Table of Contents**](#table-of-contents)
1. [**About FREAK**](#about-freak)
2. [**Technical documentation**](#technical-documentation)
   1. [**About RSA**](#about-rsa)
   2. [**DNS cache poisoning**](#dns-cache-poisoning)
   3. [**FREAK (MitM)**](#freak-mitm)
   4. [**Factorization**](#factorization)
   5. [**Breaking encryption**](#breaking-encryption)
3. [**Performing the exploit**](#performing-the-exploit)
   1. [**Using DNS cache poisoning**](#using-dns-cache-poisoning)
   2. [**Using MitM**](#using-mitm)
   3. [**Using Factorization**](#using-factorization)
4. [**Mitigation / Defense against the attack**](#1-about-freak)

---

[**Various project information**](#various-project-information)
1. [**The usage of LLM:s, AI and borrowed code**](#the-usage-of-llms-ai-and-borrowed-code)
2. [**Contribution documentation**](#contribution-documentation)
3. [**Presentation material**](#presentation-material)

## About FREAK

Broad introduction

Information on FREAK:
- https://nvd.nist.gov/vuln/detail/CVE-2015-0204 (OpenSSL)
- https://nvd.nist.gov/vuln/detail/CVE-2015-1637 (Schannel)
- https://nvd.nist.gov/vuln/detail/CVE-2015-1067 (Secure Transport)
- https://www.cisa.gov/news-events/alerts/2015/03/06/freak-ssltls-vulnerability
- https://en.wikipedia.org/wiki/FREAK
- https://access.redhat.com/articles/1369543
- https://freakattack.com/

Previous practical demonstration:

- https://github.com/eniac/faas/tree/master
- https://fc16.ifca.ai/preproceedings/19_Valenta.pdf

## Technical documentation

### About RSA

Eskil and Ioanna

### DNS cache poisoning

The DNS cache poisoning is done by sending a DNS request for a domain and then flood the DNS server with fake responses, hoping our response reaches the server first, and is the answer that will be cached. Thus when other clients ask the server for said domain, our faulty answer with a different IP will be served. We host our man-in-the-middle proxy which forwards the traffic to the real server. Making the clients not able to easily detect that something is wrong.

For a fake request to be treated as valid two things must be true:
- The transaction ID must be the same for the answer as the query the DNS server sent 
- It must be sent to the correct port on the DNS server

There are two scenarios for this:
- We are on the same network as the DNS server
- We are on a different network as the DNS server

If we are on the same network, we can sniff the DNS request and read both the transaction ID and the port number from the request. Construct our response and send it, since we are on the local network we have a high probabilty to be faster than the remote DNS server it is quering.

If we are on a different network things become a bit more complicated. We have to guess both values. The transaction ID is a 16-bit number, and the port number is also a 16-bit number. The port number was usually a fixed port on older DNS server, but is being randomized for modern systems for security, similar to ASLR. To make the attack easier for our demonstration we set a fixed port number (see [named.conf.options:L8](https://github.com/LogFlames/DD2391-project/blob/6cbb1abdb9bbd189f7668d947fa74f0259bc636b/dns_cache_poisoning/dns_server/named.conf.options#L8)), however the same brute-forcing can be applied to the port as well as the transaction ID, it will just take longer. The transaction ID is being brute-forced. We use a C script ([flood.c](https://github.com/LogFlames/DD2391-project/blob/main/dns_cache_poisoning/attack/flood.c)) to efficiently generate and send UDP packets. Since the real server usually responds in a couple of milliseconds, the attack succedes if the transaction ID is lower (tested earlier in our attack script). The script must also generate manuall UDP packets to be able to pretend they originate from the IP that the DNS server expects (9.9.9.9 in our case).

Additionally, for the DNS cache poisoning to work we must disable DNSSEC. DNSSEC is a security extension formalized in 2004 (RFC3833), which add signatures to ensure only valid DNS responses are considered. There are however many DNS server today which do not use DNSSEC.

There are other ways to get a MitM attack. Two prominent alternatives are ARP spoofing and DHCP spoofing, both done on local networks.

### FREAK (MitM)

Alexandru

### Factorization

Given a number $N$ that we want to factor, the **Quadratic Sieve (QS) algorithm** aims to find numbers $x, y$ such that: $$ x^2 \equiv y^2 \pmod{N} \text{ and } x \not\equiv\pm  y \pmod{N} $$

Such a pair of numbers fulfills: $$ x^2 \equiv y^2 \pmod{N} \implies (x-y)(x+y) \equiv 0 \pmod{N} $$ and therefore, the untrivial factors of $N$ can be obtained via the greatest common divisor: $$\gcd{(x-y, N)} \text{ and } \gcd{(x+y, N)}$$

The main idea of QS is to find values of $x$ for which $Q(x) = x^2 - N$ factors completely over the factor base – a set of prime numbers less than some bound $B$. For a prime number $p$ to be in the factor base, two things must be true: $$ (p < B) \text{ and } (N \text{ is a quadratic residue } \pmod{p})$$

If $N$ is not a quadratic residue $\pmod{p}$ for some prime $p$, then $Q(x)$ will never be divisible by $p$ for any value of $x$, and therefore such primes are not useful to the QS algorithm. We use Euler's criterion to compute the Legendre symbol and filter out such primes.

Next, for each prime $p$ in the factor base we find all the roots $r$ $\pmod{p}$ of this equation: $$x^2 \equiv N \pmod{p}$$ meaning, we find all values of $x$ for which $p$ divides $Q(x)$. For each root $r$, every $$ x \equiv r \pmod{p} \text{ will make } p|(x^2−n)$$.

From all the different $Q(x)$ values, we keep only those that can fully factor over the factor base, meaning all the factors are from the factor base and only the factor base – these are called $B$-smooth numbers. For each $B$-smooth number we keep a relation – a vector of exponents $\pmod{2}$ for each prime in the factor base.

Once the relations have been agthered, we build an $R \times B$ matrix, where $B$ is the number of primes in the factor base and $R$ the number of $B$-smooth numbers. Row $i$ the relation of $Q(x_i)$.

We are looking for a subset of rows such that the sum of each exponent is congruent to $0 \pmod{2}$. This will ensure that the product of the corresponding $Q(x)$ values forms a perfect square, yielding a factorization of $N$.

The **One-Large-Prime (1LP) variant** is an optimization of the basic QS algorithm. In the basic QS, only values $Q(x)$ that are completely $B$-smooth (_full_ relations) are accepted, whereas the 1LP variant also accepts _partial_ relations – $Q(x)$ values that factor over the factor base except for one extra “large” prime slightly above the bound $B$.
These partial relations are stored and temporarily and latered combined into pairs that share the same large prime. When two partial relations are multiplied together, the large prime acquires an even exponent that cancels out $\pmod{2}$, thus producing a full relation.
This way, the number of usable relations is increased without great computational increase.


The **General Number Field Sieve (GNFS) algorithm** shares the same core concept with the Quadratic Sieve - finding $B$-smooth numbers and solvinf a matrix of congruences – but unlike QS, it uses multiple polynomials defined over higher-degree algebraic number fields and generates relations in both the rational and algebraic domains.
Some of the improvements in GNFS are:
- the use of Lattice Sieving (extension of the QS sieving in higher dimensions)
- the "Multiple-large-primes" variants (extension of the 1LP variant to two or more large primes per relation)

Essentially, it could be said that QS is a special case of GNFS, limited to the rational number field ($\mathbb{Q}$). GNFS generalizes QS and moves from working in $\mathbb{Q}$ to working in polynomial rings.

### Breaking encryption

Alexandru

## Performing the exploit

### Using DNS cache poisoning

1. Setup the environment using docker compose:
```
cd dns_cache_poisoning
docker compose build && docker compose up
```
This will start a DNS server and a client which will be used to launch the attack.

2. Test the DNS server:
The DNS server is setup to forward to port 1053 on the host.
```
dig @127.0.0.1 -p 1053 example.com
```
Ensure you get a response.

3. Run the attack:
```
docker exec -it dns_cache_poisoning-attacker-1 bash
cd /root
./attempt_main.sh
./flood.sh
```

`attempt_main.sh` will try to posion the DNS entry for `eliaslundell.se`. If it succeedes you can veriy from your host that an invalid IP address is being returned. 
```bash
dig @127.0.0.1 -p 1053 eliaslundell.se
```

> In case of a successfull attack it will return the ip address `192.168.128.128`, if the attack was not successfull it will return the ip found on [eliaslundell.se](https://mxtoolbox.com/SuperTool.aspx?action=a%3aeliaslundell.se&run=toolpage).

However, the attack might not succeed, and then you will have to wait until the cache expires to try again.

`flood.sh` will query a non existing subdomain and try to modify the cached NS record for the domain. In case the attack fails for `a.eliaslundell.se`, it will immediately try `b.eliaslundell.se` and so on.
This way it does not have to wait for the cache to expire.

#### Helpful commands on the DNS server 

```bash
docker exec -it dns_cache_poisoning-dns_server-1 bash
rndc dumpdb # To dump the cache into /var/cache/bind/dump.db which can be viewed to verify the attack was successfull
rndc flush # To clear the cache to attempt the main attack again quicker for testing
```

### Using MitM

Alexandru

### Using factorization

Eskil and Ioanna

## Mitigation/Defense against the attack

Todo

## DD2391 Project Final 18

By: Alexandru Carp, Elias Lundell, Eskil Nyberg, Venetia Ioanna Papadopoulou

# Various project information

## The usage of LLM:s, AI and borrowed code

TODO

## Contribution documentation

### Alexandru Carp

TODO

### Elias Lundell

TODO

### Eskil Nyberg

TODO

### Venetia Ioanna Papadopoulou

TODO

## Presentation material

Google Slides: [DD2391 Project - Final Group 18 - FREAK](https://docs.google.com/presentation/d/1Ma8DdMEyfZuG2-iaYIO6c-XB07Kh5vx1UhjnjDeAjVI/edit?usp=sharing)
