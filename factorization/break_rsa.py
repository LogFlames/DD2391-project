#!/usr/bin/env python3
"""
Wrapper script for running the implemented QS algorithm for an RSA modulus.
    Input:  N (assumed to be an RSA modulus, i.e., product of two primes)
    Output: the factors of N

Written with LLM assistance.
"""

import argparse
import quadratic_sieve
import re
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa

def read_n_from_pubkey(filename):
    with open(filename, 'r') as f:
        content = f.read()
    match = re.search(r'-----BEGIN PUBLIC KEY-----(.*?)-----END PUBLIC KEY-----', content, re.DOTALL)
    if match:
        # PEM format: decode base64, parse ASN.1, extract modulus

        keydata = base64.b64decode(''.join(match.group(1).split()))
        pubkey = serialization.load_der_public_key(keydata, backend=default_backend())
        numbers = pubkey.public_numbers()
        return numbers.n
    else:
        raise ValueError("No valid public key found in the file.")

def factor_rsa_modulus(N):
    p = quadratic_sieve.quadratic_sieve(N)
    if 1 < p < N:
        q = N // p
        assert p * q == N
        return True, p, q
    return False, None, None

def generate_private_key(p, q, e):
    phi = (p - 1) * (q - 1)
    d = pow(e, -1, phi)
    return d

def main():
    parser = argparse.ArgumentParser(description="Quadratic Sieve Factorization")
    parser.add_argument("-f", "--pubkey", type=str, help="Path to PEM-formatted RSA public key file")
    parser.add_argument("-N", type=int, help="RSA modulus to factor (composite integer)")
    parser.add_argument("-e", type=int, default=65537, help="Public exponent (default: 65537)")
    parser.add_argument("--outfile", type=str, help="Output file for private key (if pubkey provided)")
    args = parser.parse_args()

    if not args.pubkey and not args.N:
        print("Please provide either a public key file or an integer N.")
        return
    
    if args.outfile and not args.pubkey:
        print("Output file specified without a public key. Ignoring outfile argument.")
        args.outfile = None

    if args.pubkey and args.N:
        print("Please provide either a public key file or an integer N, not both.")
        return

    if args.pubkey:
        try:
            N = read_n_from_pubkey(args.pubkey)
            print(f"Read modulus N from public key: {N}")
        except Exception as e:
            print(f"Error reading public key: {e}")
            return    
    else:
        N = args.N
        print(f"Using provided modulus N: {N}")

    if N <= 1:
        print("N must be a composite integer greater than 1.")
        return

    print(f"Calling Quadratic Sieve to factor N...")
    ok, p, q = factor_rsa_modulus(N)
    if ok:
        print(f"""Factorization successful!
              {N} =
              {p}
              *
              {q}
              """)
    else:
        print(f"ERROR: Factorization unsuccessful.")
        return
    
    if args.pubkey:
        e = args.e
        print(f"Generating private key with e={e}...")
        d = generate_private_key(p, q, e)
        print(f"Private exponent d: {d}")

        if args.outfile:
            with open(args.outfile, 'w') as f:
                private_numbers = rsa.RSAPrivateNumbers(
                    p=p,
                    q=q,
                    d=d,
                    dmp1=d % (p - 1),
                    dmq1=d % (q - 1),
                    iqmp=pow(q, -1, p),
                    public_numbers=rsa.RSAPublicNumbers(e, N)
                )
                private_key = private_numbers.private_key(backend=default_backend())
                pem = private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption()
                )
                f.write(pem.decode())

if __name__ == "__main__":
    main()