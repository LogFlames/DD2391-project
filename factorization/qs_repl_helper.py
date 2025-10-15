"""
Python REPL helper functions. Run using:
$ python -i qs_repl_helper.py

or to run sieve automatically:
$ python -i qs_repl_helper.py <bits>
"""

from quadratic_sieve import *
from Crypto.Util import number

def testQuadraticSieve(bits: int):
    p = number.getPrime(bits//2)
    q = number.getPrime(bits//2)
    N = p * q
    print(f"Generated {bits}-bit / {len(str(N))}-digit composite\n| {N} = \n| {p} \n|  * \n| {q}")
    factor = quadratic_sieve(N, B="auto", DEBUG=True)
    print(f"factor: {factor}")
    assert N % factor == 0 and factor != 1 and factor != N
    print("Test passed!")

def getComposite(bits: int):
    p = number.getPrime(bits//2)
    q = number.getPrime(bits//2)
    N = p * q
    print(f"Generated {bits}-bit / {len(str(N))}-digit composite\n| {N} = \n| {p} \n|  * \n| {q}")
    return N

from sys import argv
if len(argv) == 2:
    N = testQuadraticSieve(int(argv[1]))