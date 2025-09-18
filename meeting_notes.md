# Meeting notes

## Meeting 2025-09-10

Meeting in-person with Roberto at 13.00 on Tuesday. We'll meet a little bit earlier to decide on which our primary project idea will be.

Ideas:

* Performing a web attack --- Ioanna
* Network of docker containers, exploring firewalls --- Alex
* Exploiting CVE (demonstration / e.g. Spectre) --- Eskil, Ioanna
* Implement antivirus that identifies malware --- Elias

Lab format if original idea is not too difficult.

Deadline for topic research Monday at 19.00

## Meeting 2025-09-16

### Ideas

Elias:
- Looked at anti-malware. Heuristics, "it does bad things" but gives false positives, or specific anti-malware protections. Not many malware seem very interesting.

Ioanna:
- Web hacking is mostly covered by lab W. CVE:s : [Heartbleed](https://nvd.nist.gov/vuln/detail/CVE-2014-0160), [FREAK](https://www.cisa.gov/news-events/alerts/2015/03/06/freak-ssltls-vulnerability) - breaking TLS with intentional vulnerability (weakness), [POODLE](https://nvd.nist.gov/vuln/detail/CVE-2014-3566) - reading single plaintext bytes from OpenSSL.

Alex:
- Firewall, server, internal database, client, attacker; implementing stateless firewall, stateful firewall and VPN to inspect routing and security. Could also set up honeypot. Possibly application-aware firewalls. Post-firewall monitoring also possible.

Eskil:
- Spectre, an attack that exploits branching predictions to read sensitive/insensitive data, statistical improvements, trusting-trust

### Meeting with Roberto

Info from meeting:

Possible avenues for FREAK:
- proof-of-concept
- proxy / DNS poisoning
- (efficient) factorization
- defense(s)

Firewall system + Spectre also ok.

**Repository:** documentation necessary to follow the lab / execute the code. Include short information on usage of LLM:s and any borrowed code.
**Report:** 2~3 pages
**Presentation:** ~20 minutes (possibly slightly less), questions are not graded. Attendance only necessary the date we are presenting.

Send e-mail directly to Roberto in case of questions.