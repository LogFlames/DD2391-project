# FREAK (CVE-2015-0204)

**F**actoring **R**SA **E**xport **K**eys

> FREAK ("Factoring RSA Export Keys") is a security exploit of a cryptographic weakness in the SSL/TLS protocols introduced decades earlier for compliance with U.S. cryptography export regulations. These involved limiting exportable software to use only public key pairs with RSA moduli of 512 bits or fewer (so-called RSA EXPORT keys), with the intention of allowing them to be broken easily by the National Security Agency (NSA), but not by other organizations with lesser computing resources. However, by the early 2010s, increases in computing power meant that they could be broken by anyone with access to relatively modest computing resources using the well-known Number Field Sieve algorithm, using as little as $100 of cloud computing services.
> 
> *en.wikipedia.org/wiki/FREAK, 18 sept 2025*

## Table of Contents

[**FREAK (CVE-2015-0204)**](#freak-cve-2015-0204)

0. [**Table of Contents**](#table-of-contents)
1. [**Project summary**](#project-summary)
2. [**Technical documentation**](#technical-documentation)
   1. [**About RSA**](#about-rsa)
   2. [**DNS Cache Poisoning**](#dns-cache-poisoning)
   3. [**FREAK (MitM)**](#freak-mitm)
   4. [**Factorization**](#factorization)
   5. [**Breaking encryption**](#breaking-encryption)
3. [**Performing the exploit**](#performing-the-exploit)
   1. [**Using DNS Cache Poisoning**](#using-dns-cache-poisoning)
   2. [**Using MitM**](#using-mitm)
   3. [**Using the Quadratic Sieve**](#using-the-quadratic-sieve)
4. [**Mitigation / Defense against the attack**](#mitigationdefense-against-the-attack)
5. [**References**](#references)

---

[**Various project information**](#various-project-information)
1. [**The usage of LLM:s, AI and borrowed code**](#the-usage-of-llms-ai-and-borrowed-code)
2. [**Contribution documentation**](#contribution-documentation)
3. [**Presentation material**](#presentation-material)

## Directory structure

Note: as per request, this README.md contains all details on the project necessary for the report. Other READMEs and files contain auxiliary or unnecessary information.

Overview:
* [client/](client/) - installation files for the client
* [server/](server/) - installation files for the server
* [dns_cache_poisoning/](dns_cache_poisoning/)
  * [dns_cache_poisoning/README.md](dns_cache_poisoning/README.md) - heavy details on the DNS cache poisoning and how to use it.
  * ...
* [mitm/](mitm/) - files for the MitM attack
* [factorization/](factorization/)
  * [readme.md](factorization/readme.md) - heavy details on the Quadratic Sieve and how to use it. Detailed comparisons to the GNFS.
  * [math.md](factorization/math.md) - heavy details on the math behind the Quadratic Sieve and its implementation
  * ...
* [infrastructure.md](infrastructure.md) - Details on the interworkings and infrastructure that the DNS cache poisoning and MitM uses.
* [README.md](README.md) - This file, and the project report.

## Project summary

Project summary: Eskil

<!---TODO
--->

## Technical documentation

Following is technical and theoretical background regarding the attack and the technologies involved. It serves as a guide for how we have implemented the attack and relevant considerations.

### About RSA

Eskil and Ioanna

<!---TODO
--->

### DNS Cache Poisoning

The DNS cache poisoning is done by sending a DNS request for a domain and then flood the DNS server with fake responses, hoping our response reaches the server first, and is the answer that will be cached. Thus when other clients ask the server for said domain, our faulty answer with a different IP will be served. We host our man-in-the-middle proxy which forwards the traffic to the real server. Making the clients not able to easily detect that something is wrong.

For a fake request to be treated as valid two things must be true:
- The transaction ID must be the same for the answer as the query the DNS server sent 
- It must be sent to the correct port on the DNS server

There are two scenarios for this:
- We are on the same network as the DNS server
- We are on a different network as the DNS server

If we are on the same network, we can sniff the DNS request and read both the transaction ID and the port number from the request. Construct our response and send it, since we are on the local network we have a high probabilty to be faster than the remote DNS server it is quering.

If we are on a different network things become a bit more complicated. We have to guess both values. The transaction ID is a 16-bit number, and the port number is also a 16-bit number. The port number was usually a fixed port on older DNS server, but is being randomized for modern systems for security, similar to ASLR. To make the attack easier for our demonstration we set a fixed port number (see [named.conf.options:L8](https://github.com/LogFlames/DD2391-project/blob/6cbb1abdb9bbd189f7668d947fa74f0259bc636b/dns_cache_poisoning/dns_server/named.conf.options#L8)), however the same brute-forcing can be applied to the port as well as the transaction ID, it will just take longer. The transaction ID is being brute-forced. We wrote a C script ([flood.c](dns_cache_poisoning/attack/flood.c)) to efficiently generate and send UDP packets. Since the real server usually responds in a couple of milliseconds, the attack succedes if the transaction ID is lower (tested earlier in our attack script). The script must also generate manuall UDP packets to be able to pretend they originate from the IP that the DNS server expects (9.9.9.9 in our case).

Additionally, for the DNS cache poisoning to work we must disable DNSSEC. DNSSEC is a security extension formalized in 2004 (RFC3833), which add signatures to ensure only valid DNS responses are considered. There are however many DNS server today which do not use DNSSEC.

There are other ways to get a MitM attack. Two prominent alternatives are ARP spoofing and DHCP spoofing, both done on local networks.

### FREAK (MitM)

The FREAK attack assumes a man in the middle (MitM) position between a vulnerable client and a vulnerable server. The MitM intercepts the TLS handshake messages and modifies them to downgrade the security level of the connection, allowing him to break the encryption and read or modify application data.

For the server to be vulnerable, it must support export RSA cipher suites.

For the client to be vulnerable, it must accept a ServerKeyExchange message containing a temporary RSA key in a non-export RSA handshake. This is due to a flaw in the TLS protocol implementation in some clients (e.g. OpenSSL versions before 1.0.1k).

Important TLS handshake messages involved in the FREAK attack are:

- ClientHello: sent by the client to initiate the handshake. It contains a list of supported cipher suites, which are combinations of key exchange, encryption and MAC algorithms. The MitM modifies this message to replace the original cipher suites with an export RSA cipher suite (e.g. TLS_RSA_EXPORT_WITH_DES40_CBC_SHA, 0x0008).

- ServerHello: sent by the server in response to ClientHello. It contains the selected cipher suite. If the client does not offer export ciphers originally, the MitM modifies this message to replace the selected export RSA cipher suite with one from the original ClientHello list, so that the client doesn't reject the ServerHello.

- ServerKeyExchange: sent by the server only when using export RSA cipher suites. It contains a temporary RSA public key (512 bits) generated by the server for this session. The MitM extracts this key and factors it. In non-export RSA handshakes, this message is not sent, as the server's certificate already contains the public key.

- ClientKeyExchange: sent by the client. It contains the premaster secret encrypted with the temporary RSA public key from ServerKeyExchange. The MitM captures this message to obtain the encrypted premaster secret.

- Finished messages: sent by both client and server to verify that the handshake was not tampered with. They are encrypted and contain a hash of all previous handshake messages. The MitM must modify these messages to reflect the changes made to the handshake, otherwise the client or server will abort the connection.

In theory, the client should not expect a ServerKeyExchange message in a non-export RSA handshake, and should abort the handshake if it receives one. However, due to a flaw in the TLS protocol implementation in some clients (e.g. OpenSSL versions before 1.0.1k), the client accepts the ServerKeyExchange message and uses the temporary RSA key to encrypt the premaster secret. This is what makes the FREAK attack possible. The patch of this bug can be found [here](https://git.openssl.org/gitweb/?p=openssl.git;a=commit;h=5f0d4f7f6f1b8e3f4c3e2e6f4b5a5c6c3e2e6f4b).

Another important flaw that made the attack possible was the reuse of the temporary RSA keys by the server across multiple connections, as stated [here](https://www.ieee-security.org/TC/SP2015/papers-archived/6949a535.pdf). This allowed the MitM to factor the temporary RSA key once and use it to decrypt multiple premaster secrets from different clients. Without this, the MitM would have not been able to break the encryption in time to modify the Finished messages and avoid detection.

### Factorization

To break the RSA key, we want to factorize the modulus of the public key so that we can compute the private key. The modulus is on the form $N=p*q$, where $p$ and $q$ are large primes. For **FREAK** in particular, the modulus is 512 bits (155 digits) and would require the employment of the algorithm **GNFS, the General Number Field Sieve** which is the fastest known algorithm for factoring large numbers. However, the GNFS is both:

* incredibly difficult, both to understand and to implement, requiring knowledge of number theory far beyond what we have learnt previously
* expensive, costing about $100 in cloud resources to factorize a 512-bit RSA (with the most efficient implementations known)

To appropriate the factorization to our project, we have instead elected to implement the Quadratic Sieve - the fastest algorithm known for factoring numbers smaller than 100 digits. The GNFS is based upon some of what the Quadratic Sieve uses, and thus the QS serves as an instructive example for how sieving works, without making it too difficult to understand and too costly to test.

Now we will go over (in broad terms) the maths behind the Quadratic Sieve.

#### The Quadratic Sieve

Given a number $N$ that we want to factor, the **Quadratic Sieve (QS) algorithm** aims to find numbers $x, y$ such that: $$ x^2 \equiv y^2 \pmod{N} \text{ and } x \not\equiv\pm  y \pmod{N} $$

Such a pair of numbers fulfill: $$ x^2 \equiv y^2 \pmod{N} \implies (x-y)(x+y) \equiv 0 \pmod{N} $$ and therefore, the untrivial factors of $N$ can be obtained via the greatest common divisor: $$\gcd{(x-y, N)} \text{ and } \gcd{(x+y, N)}$$

The main idea of QS is to find values of $x$ for which $Q(x) = x^2 - N$ factors completely over the factor base – a set of prime numbers less than some bound $B$. For a prime number $p$ to be in the factor base, two things must be true:

$$ (p < B) \text{\quad and\quad } (N \text{ is a quadratic residue }(\text{mod } p))$$

If $N$ is not a quadratic residue $\pmod{p}$ for some prime $p$, then $Q(x)$ will never be divisible by $p$ for any value of $x$, and therefore such primes are not useful to the QS algorithm. We use Euler's criterion to compute the Legendre symbol and filter out such primes.

Next, for each prime $p$ in the factor base we find all the roots $r$ $\pmod{p}$ of this equation: $$x^2 \equiv N \pmod{p}$$ meaning, we find all values of $x$ for which $p$ divides $Q(x)$. For each root $r$, every $x \equiv r \pmod{p}$ will make $p|(x^2−n).$

From all the different $Q(x)$ values, we keep only those that can fully factor over the factor base, meaning all the factors are from the factor base and only the factor base – these are called $B$-smooth numbers. For each $B$-smooth number we keep a relation – a vector of exponents $\pmod{2}$ for each prime in the factor base.

Once the relations have been gathered, we build an $R \times B$ matrix, where $B$ is the number of primes in the factor base and $R$ the number of $B$-smooth numbers. Row $i$ represents the relation of $Q(x_i)$.

We are looking for a subset of rows such that the sum of each exponent is congruent to $0 \pmod{2}$. This will ensure that the product of the corresponding $Q(x)$ values forms a perfect square, yielding a factorization of $N$.

##### Optimizing the Quadratic Sieve

An obvious optimization is **parallelization**. To parallelize, we split the sieving interval into many small chunks and send out the sieving tasks to several workers - which can live on different computers. This splitting also makes sieving large intervals manageable on single computers, and not all chunks have to be done concurrently.

The **One-Large-Prime (1LP) variant** is an optimization of the basic QS algorithm. In the basic QS, only values $Q(x)$ that are completely $B$-smooth (_full_ relations) are accepted, whereas the 1LP variant also accepts _partial_ relations – $Q(x)$ values that factor over the factor base except for one extra “large” prime slightly above the bound $B$.
These partial relations are stored and temporarily and latered combined into pairs that share the same large prime. When two partial relations are multiplied together, the large prime acquires an even exponent that cancels out $\pmod{2}$, thus producing a full relation.
This way, the number of usable relations is increased without great computational increase.

Lastly, there is the **Multi-Polynomial Quadratic Sieve (QLP)** which ...
<!--- TODO
--->

#### More details on the maths behind the Quadratic Sieve is available in [math.md](math.md).

#### What's missing for the GNFS?

The **General Number Field Sieve (GNFS) algorithm** shares the same core concept with the Quadratic Sieve - finding $B$-smooth numbers and solving a matrix of congruences – but unlike the QS, it uses multiple polynomials defined over higher-degree algebraic number fields and generates relations in both the rational and algebraic domains.

Essentially, it could be said that QS is a special case of GNFS, limited to the rational number field ($\mathbb{Q}$). GNFS generalizes QS and moves from working in $\mathbb{Q}$ to working in polynomial rings. More specifically, in broad terms, the parallels between the QS and GNFS are:

* Both the GNFS/SNFS and the QS look for numbers on the form $x^2=y^2\pmod{N}$.
* The factor base is instead elements of these fields.
* Sieving is done to check a bunch of polynomials for certain attributes (rather than the $Q(x)=(x+\sqrt{N})^2-N$ that the QS uses), eventually finding polynomials which fulfill a property related to B-smoothness.
* With enough relations the GNFS eventually finds squares in both number fields, which are mapped to $x^2=y^2\pmod{N}$ that we can check, in contrast to products of $Q(x)$. This is essentially analogous with how we find square products of $Q(x)$.

Some of the improvements in GNFS are:
- the use of Lattice Sieving (extension of the QS sieving in higher dimensions)
- the "Multiple-large-primes" variants (extension of the 1LP variant to two or more large primes per relation)
- due to the massive "factor base" in question, the Block Lanczos algorithm is used instead of standard Gaussian elimination to reach advertised speeds, which also partially allows parallelization.

Because the Number Field Sieves contains a lot of number theory - complex numbers, polynomials, etc. - the math and algorithm used becomes really complex really quickly.

### Breaking encryption

After obtaining the private key by factoring the RSA modulus, the attacker can decrypt the premaster secret sent by the client in the ClientKeyExchange message. With the premaster secret, the attacker can derive the master secret and subsequently compute the session keys used for encrypting and authenticating application data. This can also be easily done using tools like Wireshark, given the decrypted premaster secret.

However, as stated above, to avoid detection of the tampering and successfully complete the handshake, the attacker must modify the Finished messages sent by both client and server. These messages contain a hash of all previous handshake messages, encrypted with the session keys.

Therefore, the attacker must be able to decrypt the Finished messages, modify them to reflect the changes made to the handshake (i.e., the modified ClientHello and ServerHello messages), and then re-encrypt them with the correct session keys. This requires the attacker to perform the decryption and re-encryption in real-time, making it need to implement decryption and encryption functions for the specific cipher suite used in the handshake. 

For this demo, we implemented the decryption and re-encryption for the TLS_RSA_EXPORT_WITH_DES40_CBC_SHA cipher suite, which uses DES with 40-bit keys for encryption and SHA-1 for message authentication. Moreover, for simplicity, we assumed tls1.0 is used, which has a simpler key derivation process compared to later versions of TLS.

## Performing the exploit

### Using DNS Cache Poisoning

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

1. Setup the environment using docker compose:
```
docker compose up --build
```
This will start the server, mitm and client. The client will automatically send a first request, that is expected to fail but allows the mitm to capture the information required for the factorization step.

The factorization is simulated and not actually performed in this demo, as it would take too long. After a short wait, the mitm will print the master key in both the format used by wireshark and openssl s_client.

2. Manually create another connection from the client to the server:
```
docker exec -it freak-client /bin/bash
openssl s_client -connect freak-mitm:8443 -tls1 -no_comp
```
This connection should succeed, with the client returning 0 and with no errors logged by the server. The MitM logs show every step of the process: ClientHello tampering, all handshake messages capturing, finished message decryption, modification and re-encryption.

3. Use the master secret to decrypt the traffic in wireshark:

The mitm saves the master secret in `/pcap/keyfile.log`. In wireshark, go to Preferences -> Protocols -> TLS and set (or append to) the (Pre)-Master-Secret log filename to point to this file. Then open the pcap file `/pcap/freak_mitm.pcap` and the TLS traffic should be decrypted.

In this demo the only encrypted messages are the Finished messages, but as the connection succeeds, further encrypted application data could be captured and decrypted as well.

### Using the Quadratic Sieve

> #### Requirements
> 
> Install Python requirements with
> ```bash
> $ cd ./factorization
> $ python3 -m pip install requirements.txt
> ```

The Quadratic Sieve can be interacted with via
```bash
$ cd factorization
$ N="730263881119727212489103570233" # 100-bit number with two large prime factors

# factor N
$ python3 run.py factor -N "$N"

# generate 100-bit number and factor it
$ python3 run.py factor --bits 100

# generate 100-bit number and factor it, making use of 8 parallel jobs (processes)
$ python3 run.py factor --bits 100 -J 8
```

There are many arguments that can be passed and many more ways to run the sieve, find out more in [factorization/readme.md](factorization/readme.md).

To factorize a number for the attack, we run:
```bash
TODO!!!
```
Note that the Quadratic Sieve should only be used for small enough numbers. It is the fastest for numbers with less than 100 digits (330 bits) but that doesn't mean it is fast with such numbers: that would require parallelization across computers and more efficient code than we have written, and preferably not Python code.

Our implementation is reasonable for numbers with less than 150 bits, and fast for numbers with less than 120 bits. An estimated running time can be achieved by running the algorithm against an input (use the number of chunks, $-1$). This may still crash with large enough inputs!

For example, on our computer (8 cores, ~4 GHz, 16 GB RAM):

* 200 bits takes 5 hours.
* 220 bits takes 75 hours.
* 250 bits crashes.

## Mitigation/Defense against the attack

Todo

<!---TODO
--->

## References

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

DNS Cache Poisoning:

- https://www.cloudflare.com/learning/dns/dns-cache-poisoning/
- https://seedsecuritylabs.org/Labs_16.04/PDF/DNS_Remote.pdf
- https://www.utc.edu/sites/default/files/2021-04/dns.pdf
- https://datatracker.ietf.org/doc/html/rfc1035
- https://gieseanw.wordpress.com/2010/03/25/building-a-dns-resolver/
- https://gist.github.com/leonid-ed/909a883c114eb58ed49f

Factorization / Quadratic Sieve:

* https://www.math.unl.edu/~mbrittenham2/classwk/445f08/dropbox/landquist.quadratic.sieve.pdf
* https://gwern.net/doc/cs/cryptography/1996-pomerance.pdf

<!---TODO
Add references for Quadratic Sieve
Add references for GNFS
Add references for Alex's part?
--->

## DD2391 Project Final 18

By: Alexandru Carp, Elias Lundell, Eskil Nyberg, Venetia Ioanna Papadopoulou

# Various project information

## Notice on the usage of LLM:s, AI and borrowed code

For this project, LLM:s have been used to understand theory, and write, improve, comment, and optimize code for the various parts of the project. No code has been borrowed for this project, and AI hasn't been otherwise used.

In particular, the basic quadratic sieve was written with little-to-no input from LLM:s, i.e. the one in [factorization/src/qslib/base.py](factorization/src/qslib/base.py). Other iterations used LLM:s extensively for optimizations and so forth.

The [flood.c](dns_cache_poisoning/attack/flood.c) was initially structed by the use of LLMs but later revised and refined to work according to RFC1035 manually; little of the original LLM-generated-code is still present in the file. Parts of it (generating manual UDP packets) are based on [udp_to_remote.c](https://gist.github.com/leonid-ed/909a883c114eb58ed49f).

## Contribution documentation

### Alexandru Carp

- Researched OpenSSL versions vulnerable to FREAK and set up the client and server accordingly. Used OpenSSL 1.0.1f shipped with Ubuntu 14.04, which should have been vulnerable but later found out it was backported by ubuntu. Built it from source to ensure it was vulnerable.
- Implemented a python MitM proxy that parses and modifies TLS handshake messages to perform the FREAK downgrade attack. Used the `scapy` library to parse and manipulate handshake messages, but also implemented custom parsing logic, using wireshark to understand the structure of the messages.
- When I faced the problem of invalid Finished messages causing the handshake to abort, I tried to use SSLv2 and tried to implement a parser for it because it does not use finished hashes, but abandoned this approach when I found out that OpenSSL servers reuse the temporary RSA export keys, which made the attack feasible by also modifying the Finished messages.
- Modified the OpenSSL server code to dump the temporary RSA export key used in the handshake to a file, so that it simulates factoring it, which allows continuing the attack.
- Implemented the RSA decryption of the premaster secret using the factored private key, and the derivation of the master secret and session keys using PRF as specified in TLS 1.0. This part was tricky because of the different key derivation rules for export cipher suites.
- Implemented the decryption, modification, and re-encryption of the Finished messages to avoid detection of the tampering and successfully complete the handshake. Implementing the re-encryption was particularly challenging, because it also required MAC computation and padding, which were not as relevant for the decryption. The decryption should also work for other messages, as IV changing is implemented, but the encryption only works for the first encrypted message, which is the Finished message, because for the next ones the sequencing is not implemented and MAC verification would fail. That would not be hard to implement though, and would allow tampering any application data messages as well. However, the rest of the application data messages can also be easily decrypted using Wireshark, given the premaster secret.

### Elias Lundell

* Researched man-in-the-middle attacks, choosing DNS Cache Poisoning as the main attack to explore in the project.
* Setup a DNS testing environment in docker, setting up a Bind9 DNS server to be vulnerable to the attack.
* Wrote [flood.c](dns_cache_poisoning/attack/flood.c) to generate DNS packets according to RFC1035 and flood the DNS server with guesses for transaction IDs.
* Auotmated the attack using new subdomains, easing the attempts with new subdomains.

### Eskil Nyberg

* Together with Ioanna, did plenty of research to understand the inner workings and correct implementation of the Quadratic Sieve algorithm, along with potential optimizations of various kinds.
* Together with Ioanna, wrote [factorization/math.md](factorization/math.md) to understand and make transparent the math behind the Quadratic Sieve.
* Implemented the linear algebra for the Quadratic Sieve, in particular steps 5 and 6 in [factorization/src/qslib/base.py](factorization/src/qslib/base.py). Little to no LLM:s were used for this.
* Put the Quadratic Sieve together and verified the execution process.
* Optimized the Quadratic Sieve (with numpy, SageMath and parallelization) *LLM:s were used for this!*
* Tried many more optimizations, including numba (njit/jit), further numpy optimizations, parallelization variants (such as multithreading without Python's GIL), and SageMath (external). *LLM:s were used for this!*
* Refactored and deduplicated the code to make transparent everything behind our implementation of the Quadratic Sieve, see [factorization/qslib](factorization/src/qslib/).
* Wrote an [extensive interface](factorization/src/quadratic_sieve.py) for interaction with the Quadratic Sieve and the various variants we have tried. See [factorization/readme.md](factorization/readme.md) for details.
* Wrote interfaces to interact with the RSA modulus and prepare a private key from a public key, see [factorization/break_rsa.py](factorization/break_rsa.py). *LLM:s were used for this!*
* Hunted all the bugs associated with the above.

### Venetia Ioanna Papadopoulou

* Together with Eskil, did plenty of research to understand the inner workings and correct implementation of the Quadratic Sieve algorithm, along with potential optimizations of various kinds.
* Together with Eskil, wrote [factorization/math.md](factorization/math.md) to understand and make transparent the math behind the Quadratic Sieve.
<!---IOANNA: Change this if you want!
--->

<!---TODO
--->

## Presentation material

Google Slides: [DD2391 Project - Final Group 18 - FREAK](https://docs.google.com/presentation/d/1Ma8DdMEyfZuG2-iaYIO6c-XB07Kh5vx1UhjnjDeAjVI/edit?usp=sharing)
