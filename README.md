# FREAK (CVE-2015-0204)

**F**actoring **R**SA **E**xport **K**eys

> FREAK ("Factoring RSA Export Keys") is a security exploit of a cryptographic weakness in the SSL/TLS protocols introduced decades earlier for compliance with U.S. cryptography export regulations. These involved limiting exportable software to use only public key pairs with RSA moduli of 512 bits or fewer (so-called RSA EXPORT keys), with the intention of allowing them to be broken easily by the National Security Agency (NSA), but not by other organizations with lesser computing resources. However, by the early 2010s, increases in computing power meant that they could be broken by anyone with access to relatively modest computing resources using the well-known Number Field Sieve algorithm, using as little as $100 of cloud computing services.
> 
> *en.wikipedia.org/wiki/FREAK, 18 sept 2025*

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

Elias

### FREAK (MitM)

Alexandru

### Factorization

Eskil and Ioanna

### Breaking encryption

Alexandru

## Performing the exploit

### Using DNS cache poisoning

Elias

### Using MitM

Alexandru

### Using factorization

Eskil and Ioanna

## Mitigation/Defense against the attack

Todo

## Own Contribution

### Alexandru Carp

### Elias Lundell

### Eskil Nyberg

### Venetia Ioanna Papadopoulou

## DD2391 Project Final 18

By: Alexandru Carp, Elias Lundell, Eskil Nyberg, Venetia Ioanna Papadopoulou
