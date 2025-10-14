### Infrastructure for FREAK PoC

This document describes the infrastructure we set up to demonstrate the FREAK attack and the most interesting difficulties we encountered.

## Server

We used a simple openSSL server with a self-signed certificate. The server runs in a Ubuntu 14.04 docker container with openSSL 1.0.1f installed from source. We used this version because it still supported export ciphers. The command line argument used at server
startup `-cipher 'ALL:EXP'` enables all ciphers including export ones. This is the only requirement for the server to be vulnerable to FREAK and at the moment of FREAK's reporting, 36.7% of sites using trusted certificates were vulnerable[1].

## Client

To first test our setup we used openssl's s_client. We also used Ubuntu 14.04 with openssl 1.0.1f installed from source. Ubuntu 14.04 comes with openssl 1.0.1f by default, which should be vulnerable to FREAK as the patch was released in 1.0.1k. However, ubuntu
backported the patch in their own package and the openssl version installed by default was not actually vulnerable[2]. 

If a ClientHello includes export ciphers (or a mitm modifies it to do so ;) ) and the server supports them, the server will respond
with ServerHello, its Certificate and a ServerKeyExchange message containing a temporary RSA key. Note that the ServerKeyExchange message would not be sent in a normal RSA handshake without export ciphers, because the server's certificate already contains the public key. However, even if the old client didn't send export ciphers in ClientHello, if it receives a ServerKeyExchange message, it will accept it and use the temporary RSA key to encrypt the premaster secret. This is what makes the FREAK attack possible and what was fixed by this [commit](https://git.openssl.org/gitweb/?p=openssl.git;a=commit;h=5f0d4f7f6f1b8e3f4c3e2e6f4b5a5c6c3e2e6f4b).
The commit adds a check to verify that the ServerKeyExchange message is not sent in a non-export RSA handshake.

## MitM

We implemented a python proxy that intercepts TCP traffic between the client and server. It reads TLS records one by one, based
on their headers, and parses the relevant handshake messages. It modifies the ClientHello to replace non-export ciphers with an export one (0x0008) and forwards it to the server. It also intercepts the ServerHello and replaces the chosen cipher with one from the original ClientHello list, so that the client doesn't reject the ServerHello. Finally, it intercepts the ServerKeyExchange message and extracts the temporary RSA key (TODO). The proxy uses the `scapy` library to parse handshake messages. 

Support for SSLv2 is WIP.

## SSLv2 vs TLS

The current setup tricks the server into generating and using a 512-bit temporary RSA key, and also tricks the client into accepting it. However, after each of them sends the ChangeCipherSpec message, the first encrypted message sent by each is the Finished message, which contains a hash of the entire handshake as it was perceived by each party. Since the handshake was modified by the mitm, the hashes will not match and the connection will be terminated. There are two ways to solve this:
1. Break the key in no time and modify the Finished message to contain the hashes of malformed messages. This is not feasible with a 512-bit RSA key.
2. Make the client and server use SSLv2 instead of TLS. SSLv2 only include the hash of the master secret in the Finished message,
which we don't need to modify.

SSLv2 is not listed as a requirement for FREAK in online resources, which however provide little detail on the actual attack. Moreover, FREAK's wikipedia page mentions `the fact that the finished hash only depended on the master secret` [3] which is only
true for SSLv2.

We have to also test with other vulnerable clients as they might not care about the digest error and accept the connection anyway.

## Vulnerable Browser

Internet explorer 11 in Windows 7 is vulnerable to FREAK. This [VM](https://archive.org/download/modern.ie-vm/IE11.Win7.VirtualBox.zip) can be used to test the attack from a browser. [WIP]

## References

[1] https://blog.cryptographyengineering.com/2015/03/03/attack-of-week-freak-or-factoring-nsa/

[2] https://ubuntu.com/security/CVE-2015-0204

[3] https://en.wikipedia.org/wiki/FREAK