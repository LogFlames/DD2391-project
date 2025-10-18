import hmac
import hashlib
from Crypto.Cipher import ARC4

class TLSSession:
    def __init__(self, session_id: str | None = None):
        # Identity
        self.id = session_id
        self.client_addr = None
        self.server_addr = None

        # RSA params (export key)
        self.n = None
        self.e = None
        self.d = None
        self.p = None
        self.q = None

        # Handshake artifacts
        self.client_random = None
        self.server_random = None
        self.enc_pre_master_secret = None
        self.pre_master_secret = None
        self.master_secret = None
        self.key_block = None
        self.client_hello = None
        self.server_hello = None
        self.tampered_client_hello = None
        self.tampered_server_hello = None


        self.handshake_messages_client_view = b''
        self.handshake_messages_server_view = b''

        self.client_change_cipher_spec = False
        self.server_change_cipher_spec = False
        self.last_iv_client = None
        self.last_iv_server = None
        self.first_iv_client = None
        self.first_iv_server = None
        self.client_key = None
        self.server_key = None
        self.client_mac_key = None
        self.server_mac_key = None

        # Internal flags
        self._printed_master = False

    def get_master_secret(self):
        if self.master_secret != None:
            return self.master_secret
        if self.d is None or self.n is None:
            return None
        if self.enc_pre_master_secret is None:
            return None
        # Decrypt pre_master_secret using RSA private key (n, d)
        pms = self._rsa_pkcs1_v1_5_decrypt(self.enc_pre_master_secret)
        if pms is None:
            return None
        self.pre_master_secret = pms
        # Compute master_secret from pre_master_secret, client_random, server_random (TLS 1.0 PRF MD5/SHA1)
        if self.client_random is None or self.server_random is None:
            return None
        seed = self.client_random + self.server_random
        self.master_secret = self._tls10_prf(self.pre_master_secret, b"master secret", seed, 48)
        return self.master_secret

    def try_print_master_secret(self, logger=None):
        """If we have enough material, compute and print the master secret once.
        Prints in NSS key log format for easy tooling: 'CLIENT_RANDOM <client_random> <master_secret>'.
        """
        if self._printed_master:
            return
        ms = self.get_master_secret()
        if ms is None:
            return
        if self.client_random is None:
            return
        line = f"CLIENT_RANDOM {self.client_random.hex()} {ms.hex()}"
        if logger is not None:
            logger.info(line)
            # Also print in OpenSSL s_client session format for convenience
            logger.info(f"Master-Key: {ms.hex()}")
            logger.info(f"Pre-Master-Key: {self.pre_master_secret.hex()}")
            logger.info(f"Client Random: {self.client_random.hex()}")
            logger.info(f"Server Random: {self.server_random.hex()}")
        else:
            print(line)
            print(f"Master-Key: {ms.hex()}")
        self._printed_master = True

    def get_key_block(self):
        """Derive the TLS key block from the master secret and randoms.
        Returns the key block bytes or None if not enough material.
        """

        if self.key_block is not None:
            return self.key_block
        ms = self.get_master_secret()
        if ms is None:
            return None
        if self.client_random is None or self.server_random is None:
            return None
        seed = self.server_random + self.client_random

        key_block = self._tls10_prf(ms, b"key expansion", seed, 128)
        self.key_block = key_block
        return key_block
    
    def compute_stream_keys(self):
        # ensure we have key material
        key_block = self.get_key_block()
        if key_block is None or self.client_random is None or self.server_random is None:
            return None

        # Layout for DES40+SHA:
        # client_write_MAC_secret: 20 bytes
        # server_write_MAC_secret: 20 bytes
        # client_write_key: 5 bytes (exported)
        # server_write_key: 5 bytes (exported)
        client_write_mac = key_block[0:20]
        server_write_mac = key_block[20:40]
        client_write_key = key_block[40:45]
        server_write_key = key_block[45:50]

        # Derive final 16-byte PRF outputs then take first 8 bytes as DES key
        final_client = self._tls10_prf(client_write_key, b"client write key", self.client_random + self.server_random, 16)
        final_server = self._tls10_prf(server_write_key, b"server write key", self.client_random + self.server_random, 16)
        final_client_key = final_client[:8]
        final_server_key = final_server[:8]

        # IV block as specified
        iv_block = self._tls10_prf(b"", b"IV block", self.client_random + self.server_random, 16)
        client_write_iv = iv_block[0:8]
        server_write_iv = iv_block[8:16]
        self.first_iv_client = client_write_iv
        self.first_iv_server = server_write_iv
        self.last_iv_client = client_write_iv
        self.last_iv_server = server_write_iv
        self.client_key = final_client_key
        self.server_key = final_server_key
        self.client_mac_key = client_write_mac
        self.server_mac_key = server_write_mac
    def re_encrypt_first_tls(self, data: bytes, from_client: bool = True) -> bytes | None:
        """
        Re-encrypt TLS_RSA_EXPORT_WITH_DES40_CBC_SHA encrypted records using the first IV.
        Implements key/IV derivation per export-DES40 specification and
        performs DES-CBC encryption (with PKCS#7 padding addition).

        Note: this does not compute the MAC; it only encrypts with the first IV.
        """

        if self.client_key is None or self.server_key is None:
            self.compute_stream_keys()

        key = self.client_key if from_client else self.server_key
        iv = self.first_iv_client if from_client else self.first_iv_server

        # DES-CBC encrypt
        try:
            from Crypto.Cipher import DES
        except Exception as e:
            raise ImportError("pycryptodome (Crypto.Cipher.DES) is required for DES encryption") from e

        mac = self._tls10_hmac_md5(self.client_mac_key if from_client else self.server_mac_key, 0,
                                   23,  # content type: application data
                                   b'\x03\x01',  # version: TLS 1.0
                                   data)
        data_to_encrypt = data + mac
        # PKCS#7 padding (block size 8)
        pad_len = 8 - (len(data_to_encrypt) % 8)
        padded_data = data_to_encrypt + bytes([pad_len] * pad_len)

        cipher = DES.new(key, DES.MODE_CBC, iv)
        ciphertext = cipher.encrypt(padded_data)

        return ciphertext
    def decrypt_tls(self, data: bytes, from_client: bool = True) -> bytes | None:
        """
        Decrypt TLS_RSA_EXPORT_WITH_DES40_CBC_SHA encrypted records.
        Implements key/IV derivation per export-DES40 specification and
        performs DES-CBC decryption (with PKCS#7 padding removal).

        Note: this does not verify the MAC; it only decrypts and strips padding.
        """

        if self.client_key is None or self.server_key is None:
            self.compute_stream_keys()

        key = self.client_key if from_client else self.server_key
        iv = self.last_iv_client if from_client else self.last_iv_server

        # DES-CBC decrypt
        try:
            from Crypto.Cipher import DES
        except Exception as e:
            raise ImportError("pycryptodome (Crypto.Cipher.DES) is required for DES decryption") from e

        cipher = DES.new(key, DES.MODE_CBC, iv)
        plaintext = cipher.decrypt(data)

        if from_client:
            self.last_iv_client = data[-8:]
        else:
            self.last_iv_server = data[-8:]

        return plaintext

        # # Remove PKCS#7 padding (block size 8)
        # if not plaintext:
        #     return plaintext
        # pad_len = plaintext[-1]
        # if pad_len < 1 or pad_len > 8:
        #     # invalid padding length; return raw plaintext to aid debugging
        #     return plaintext
        # return plaintext[:-pad_len]

    def compute_verify_data(self, from_client: bool = True) -> bytes | None:
        """Compute the 'verify_data' for the Finished message based on the handshake messages seen.
        Uses TLS 1.0 PRF with MD5/SHA1 as per spec.
        Returns the 12-byte verify_data or None if not enough material.
        """
        ms = self.get_master_secret()
        if ms is None:
            return None
        if from_client:
            handshake_messages = self.handshake_messages_server_view
            label = b"client finished"
        else:
            handshake_messages = self.handshake_messages_client_view
            label = b"server finished"
        # Hash handshake messages with MD5 and SHA1
        md5_hash = hashlib.md5(handshake_messages).digest()
        sha1_hash = hashlib.sha1(handshake_messages).digest()
        seed = md5_hash + sha1_hash
        verify_data = self._tls10_prf(ms, label, seed, 12)
        return verify_data

    def _rsa_pkcs1_v1_5_decrypt(self, ciphertext: bytes) -> bytes | None:
        """Minimal RSA PKCS#1 v1.5 decryption using (n, d).
        Returns the decrypted pre-master secret (48 bytes) or None on failure.
        """
        try:
            k = (self.n.bit_length() + 7) // 8
            c = int.from_bytes(ciphertext, 'big')
            m = pow(c, self.d, self.n)
            em = m.to_bytes(k, 'big')  # EM = 0x00 || 0x02 || PS || 0x00 || M
            # Validate PKCS#1 v1.5 structure
            if len(em) < 11 or em[0] != 0x00 or em[1] != 0x02:
                return None
            # Find 0x00 separator after at least 8 nonzero padding bytes
            try:
                sep_idx = em.index(0x00, 2)
            except ValueError:
                return None
            if sep_idx < 10:  # must have at least 8 bytes of PS
                return None
            pms = em[sep_idx+1:]
            # Pre-master secret for RSA is expected 48 bytes
            if len(pms) != 48:
                # Some servers might include version check failures; ignore strict length
                # but if it's clearly wrong (empty), bail.
                if len(pms) == 0:
                    return None
            return pms
        except Exception:
            return None

    def _p_hash(self, secret: bytes, seed: bytes, out_len: int, hash_fn):
        result = b''
        A = seed
        while len(result) < out_len:
            A = hmac.new(secret, A, hash_fn).digest()
            result += hmac.new(secret, A + seed, hash_fn).digest()
        return result[:out_len]

    def _tls10_prf(self, secret: bytes, label: bytes, seed: bytes, out_len: int) -> bytes:
        # TLS 1.0/1.1 PRF = P_MD5(S1, label+seed) XOR P_SHA-1(S2, label+seed)
        s1 = secret[: (len(secret) + 1) // 2]
        s2 = secret[len(secret) // 2:]
        data = label + seed
        md5_bytes = self._p_hash(s1, data, out_len, hashlib.md5)
        sha1_bytes = self._p_hash(s2, data, out_len, hashlib.sha1)
        return bytes(a ^ b for a, b in zip(md5_bytes, sha1_bytes))

    def _tls10_hmac_md5(self, mac_key: bytes, seq_num: int, content_type: int,
                   version: bytes, plaintext: bytes) -> bytes:
        seq = seq_num.to_bytes(8, 'big')
        length = len(plaintext).to_bytes(2, 'big')
        mac_input = seq + bytes([content_type]) + version + length + plaintext
        return hmac.new(mac_key, mac_input, hashlib.md5).digest()