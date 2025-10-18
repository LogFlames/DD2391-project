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
The commit adds a check to verify that the ServerKeyExchange message is not sent in a non-export RSA handshake. If the check
detects an anomaly it aborts the handshake and returns UnexpectedMessage. This is what was happening when we tried to test our mitm
with the 1.0.1f client that comes with ubuntu 14.04, before we realized the patch was backported.

## MitM

We implemented a python proxy that intercepts TCP traffic between the client and server. It reads TLS records one by one, based
on their headers, and parses the relevant handshake messages. It modifies the ClientHello to replace non-export ciphers with an export one (0x0008) and forwards it to the server. It also intercepts the ServerHello and replaces the chosen cipher with one from the original ClientHello list, so that the client doesn't reject the ServerHello. Then, it intercepts the ServerKeyExchange message and extracts the temporary RSA key. If the key is broken, it uses the private key to decrypt the pre master secret sent by the client. Using that, the master secret and symmetric keys are obtained, allowing for reading and tampering encrypted messages. The MitM also recomputes the Finished digest hash to allow the connection continue after the handshake.

Support for SSLv2 was added but only works for ClientHello messages. It was later abandoned as explained in the next section.

## SSLv2 vs TLS

The current setup tricks the server into generating and using a 512-bit temporary RSA key, and also tricks the client into accepting it. However, after each of them sends the ChangeCipherSpec message, the first encrypted message sent by each is the Finished message, which contains a hash of the entire handshake as it was perceived by each party. Since the handshake was modified by the mitm, the hashes will not match and the connection will be terminated. There are two ways to solve this:
1. Break the key in no time and modify the Finished message to contain the hashes of malformed messages. This is not feasible with a 512-bit RSA key.
2. Make the client and server use SSLv2 instead of TLS. SSLv2 only include the hash of the master secret in the Finished message,
which we don't need to modify.

SSLv2 is not listed as a requirement for FREAK in online resources, which however provide little detail on the actual attack. Moreover, FREAK's wikipedia page mentions `the fact that the finished hash only depended on the master secret` [3] which is only
true for SSLv2.

We discovered another security flaw that offer a 3rd way to solve the Finished message problem. This paper [4] mentions that affected servers were reusing the temporary RSA keys for days, which makes it possible to:

1. Tamper a ClientHello to request an export cipher, capture the temporary RSA key from the ServerKeyExchange message and start
    breaking it, even if the current session will fail at the Finished message.
2. After the key is factored, tamper another ClientHello to request the same export cipher, capture the new ServerKeyExchange message and if it uses the same temporary RSA key, decrypt and modify the Finished messages to match the expected hashes.

This is the approach that we implemented, leading to abandon SSLv2 support. 

## TLS1.0 Master Key, Key derivation, and Finished message

After decrypting the premaster secret with the factored temporary RSA key, the mitm needs to derive the master secret, which is then
used to derive the symmetric keys for encryption and MAC. This is done according to the TLS1.0 specification with the help of a pseudo-random function (PRF) that combines MD5 and SHA-1 hashes. Firstly, the master secret is derived from the premaster secret, client random and server random. Then, the key block is derived from the master secret, server random and client random. The key block is then split into the required keys and IVs for both client and server. The rules for key block splitting depend on the selected cipher suite and are different for export ciphers. Finally, the Finished message is also computed using the PRF with the master secret and a concatenation of all handshake messages exchanged so far as input. 

Once all keys are obtained, symmetric decryption of messages is straight forward. However, for tampering the Finished message, we had to also re-encrypt it after modifying its content. This requires computing a new MAC for the modified Finished message, which is encrypted along with the message itself. Therefore we had to also implement the MAC computation according to the TLS1.0 specification and the selected cipher suite.


## Conclusion

While the FREAK attack seems simple in theory, the actual implementation is quite complex due to the number of details involved in a TLS handshake and record processing. With so many cryptographic artifacts to handle and so little debug information available on them,
it is very easy to make small mistakes that lead to completely different results, thus breaking the connection. Even though TLS1.0 and
export RSA ciphers are weak and obsolete standards, closely working with them made us appreciate the complexity of modern secure communication protocols and the challenges in implementing them correctly.

## Vulnerable Browser

Internet explorer 11 in Windows 7 is vulnerable to FREAK. This [VM](https://archive.org/download/modern.ie-vm/IE11.Win7.VirtualBox.zip) can be used to test the attack from a browser.

Instructions to setup the VM:
1. Download and unzip the VM image, then import it in VirtualBox (File -> Import Appliance).
2. Create a Host-Only network adapter in VirtualBox (File -> Tools -> Network Manager -> Host-Only Networks -> Create).
3. Set the VM's network adapter to Host-Only and select the adapter created in the previous step.
4. On the host, check your IP address on the Host-Only network (e.g. `ip addr show vboxnet0`).
5. Start the VM and connect to the host using the previously determined IP address (e.g. `https://<host-ip>`).


We didn't have time to test the attack with the browser, it might require additional tweaks to the mitm proxy like support for compression or other extensions.

## References

[1] https://blog.cryptographyengineering.com/2015/03/03/attack-of-week-freak-or-factoring-nsa/

[2] https://ubuntu.com/security/CVE-2015-0204

[3] https://en.wikipedia.org/wiki/FREAK

[4] https://www.ieee-security.org/TC/SP2015/papers-archived/6949a535.pdf