#!/usr/bin/env python3
"""
!!! NOTE: Run this file with ../run.py! !!!

Master file for the Quadratic Sieve implementation.

Because of differing versions of the sieve, with different dependencies,
the implementations are split into different files.

This file provides an interface to work with the various files.
You can interact with the sieve...
- in Python
>  from quadratic_sieve import <variant>_QS
- in command line
>  python -m quadratic_sieve -h
- in Python REPL
>  python -i quadratic_sieve.py -h

The available variants are:
>   base        for src.qslib.base.quadratic_sieve
>   np          for src.qslib.np_sieving.quadratic_sieve
>   parallel    for src.qslib.parallel_np_sieving.quadratic_sieve
>   complete    for src.qslib.complete.quadratic_sieve
>   max63bit    for src.qslib.np_sieving_max63bit.quadratic_sieve
>   olp         for src.qslib.one_large_prime.quadratic_sieve
>   sagemath    for src.qslib.sagemath_linalg.quadratic_sieve

---

The fastest implementation (possible in Python) is
>   src.qslib.parallel_np_sieving.quadratic_sieve
which uses numpy-accelerated sieving in parallel processes.

The easiest implementation to understand is
>   src.qslib.base.quadratic_sieve
which is a straightforward implementation of the Quadratic Sieve algorithm.

The standard implementation is
>   src.qslib.complete.quadratic_sieve
which is a superset of the parallel_np_sieving version,
adding debug output, timing, and retry logic.

---

The "QS" shorthand is used to reference the quadratic sieve.
"""

import sys
from typing import Literal

aliases = {
    "base": "src.qslib.base.quadratic_sieve",
    "np": "src.qslib.np_sieving.quadratic_sieve",
    "parallel": "src.qslib.parallel_np_sieving.quadratic_sieve",
    "complete": "src.qslib.complete.quadratic_sieve",
    "max63bit": "src.qslib.np_sieving_max63bit.quadratic_sieve",
    "olp": "src.qslib.one_large_prime.quadratic_sieve",
    "sagemath": "src.qslib.sagemath_linalg.quadratic_sieve",
}

DEBUG = 0 # default, can be changed by argument
TIMING = False # default, can be changed by argument

def base_QS(N: int, B: int="auto", **kwargs):
    """Alias for src.qslib.base.quadratic_sieve.quadratic_sieve"""
    print(f"Ignoring {kwargs} for base_QS")
    import src.qslib.base
    return src.qslib.base.quadratic_sieve(N, B)

def np_QS(N: int, B: int="auto", **kwargs):
    """Alias for src.qslib.np_sieving.quadratic_sieve.quadratic_sieve"""
    print(f"Ignoring {kwargs} for np_QS")
    import src.qslib.np_sieving
    return src.qslib.np_sieving.quadratic_sieve(N, B), src.qslib.np_sieving

def parallel_QS(N: int, B: int="auto", **kwargs):
    """Alias for src.qslib.parallel_np_sieving.quadratic_sieve.quadratic_sieve"""
    print(f"Ignoring {kwargs} for parallel_QS")
    import src.qslib.parallel_np_sieving
    return src.qslib.parallel_np_sieving.quadratic_sieve(N, B), src.qslib.parallel_np_sieving

def complete_QS(N: int, B: int="auto", num_jobs: int=4, num_parallel_jobs: int=4, retries: int=0, retry_factor: float=1.2, multivariant: Literal["multithreaded", "multiprocessing"]="multiprocessing", debug: int=0, timing: bool=TIMING):
    """Alias for src.qslib.complete.quadratic_sieve.quadratic_sieve"""
    import src.qslib.complete
    return src.qslib.complete.quadratic_sieve(N, B, num_jobs=num_jobs, num_parallel_jobs=num_parallel_jobs, retries=retries, retry_factor=retry_factor, multivariant=multivariant, debug=debug, timing=timing), src.qslib.complete

def max63bit_QS(N: int, B: int="auto", **kwargs):
    """Alias for src.qslib.np_sieving_max63bit.quadratic_sieve.quadratic_sieve"""
    print(f"Ignoring {kwargs} for max63bit_QS")
    import src.qslib.np_sieving_max63bit
    return src.qslib.np_sieving_max63bit.quadratic_sieve(N, B), src.qslib.np_sieving_max63bit

def olp_QS(N: int, B: int="auto", num_jobs: int=1, num_parallel_jobs: int=1, multivariant: Literal["multiprocessing", "multithreading"]="multiprocessing"):
    """Alias for src.qslib.one_large_prime.quadratic_sieve.quadratic_sieve"""
    import src.qslib.one_large_prime
    return src.qslib.one_large_prime.quadratic_sieve(N, B, num_jobs=num_jobs, num_parallel_jobs=num_parallel_jobs, multivariant=multivariant), src.qslib.one_large_prime

def sagemath_QS(N: int, B: int="auto", **kwargs):
    """Alias for src.qslib.sagemath_linalg.quadratic_sieve.quadratic_sieve"""
    print(f"Ignoring {kwargs} for sagemath_QS")
    import src.qslib.sagemath_linalg
    return src.qslib.sagemath_linalg.quadratic_sieve(N, B), src.qslib.sagemath_linalg

def testQuadraticSieve(variant_func,
        bits: int=None,
        N: int=None,
        debug: Literal[0, 1, 2]=DEBUG,
        timing: bool=TIMING,
        **kwargs):
    if bits is None and N is None:
        raise ValueError("One of bits or N must be provided.")
    if bits is not None and N is not None:
        raise ValueError("Only one of bits or N must be provided.")
    
    if N is None:
        N = getComposite(bits)
    else: print(f"Factoring provided number N ({N.bit_length()}-bit, {len(str(N))} digits):\n| {N}")

    if variant_func.__name__ == "complete_QS":
        kwargs.setdefault("debug", debug)
        kwargs.setdefault("timing", timing)
    
    factor, module = variant_func(N, **kwargs)
    if timing:
        module.print_timing()
    print(f"Returned factor: {factor}")
    assert N % factor == 0 and factor != 1 and factor != N
    print("Test passed!")

def getComposite(bits: int):
    import Crypto.Util.number as number

    p = number.getPrime(bits//2)
    q = number.getPrime(bits//2 + (1 if bits % 2 else 0))
    N = p * q
    print(f"Generated {bits}-bit / {len(str(N))}-digit composite\n| {N} = \n| {p} \n|  * \n| {q}")
    return N
    

def main():
    import sys
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", default="factor", choices=["factor", "list_variants", "repl"],
                        help="Mode to run: 'factor' to factor a number, 'list_variants' to list available variants, or 'repl' to start a Python REPL`.")
    parser.add_argument("-M", "--module", default="complete", type=str, choices=list(aliases.keys()),
                        help="Module (Quadratic Sieve variant) to use.")
    parser.add_argument("-b", "--bits", type=int, default=None,
                        help="Number of bits of the composite number to generate and factor (incompatible with --number).")
    parser.add_argument("-n", "--number", type=int, default=None,
                        help="Composite number to factor (overrides --bits).")
    parser.add_argument("-J", "--num-jobs", type=int, default=4,
                        help="(Only compatible with some variants.) Number of jobs for parallel variants.")
    parser.add_argument("-MJ", "--num-parallel-jobs", type=int, default=4,
                        help="(Only compatible with some variants.) Number of parallel jobs for parallel variants.")
    parser.add_argument("-R", "--retries", type=int, default=0,
                        help="(Only compatible with some variants.) Number of retries on failure.")
    parser.add_argument("-RF", "--retry-factor", type=float, default=1.2,
                        help="(Only compatible with some variants.) Factor to increase parameters by on each retry.")
    parser.add_argument("-PV", "--parallelization-variant", type=str, default="multiprocessing", choices=["multiprocessing", "multithreading"],
                        help="(Only compatible with some variants.) Parallelization variant to use. Recommended: multiprocessing.")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="(Only compatible with some variants.) Default debug level to 1.")
    parser.add_argument("-vv", "--very-verbose", action="store_true",
                        help="(Only compatible with some variants.) Default debug level to 2.")
    parser.add_argument("-t", "--timing", action="store_true",
                        help="(Only compatible with some variants.) Enable timing by default.")
    
    try:
        args = parser.parse_args()
    except SystemExit:
        sys.exit(0)

    if args.mode == "repl":
        print("Entering REPL mode. You can now use the quadratic sieve variants directly.\nOther arguments are disregarded.")
        print("Available variants:")
        for alias in aliases.keys():
            print(f" - {alias}_QS")
        import code
        code.interact(local=globals())
        return

    if args.mode == "list_variants":
        print("Available Quadratic Sieve variants:")
        for alias, fullname in aliases.items():
            print(f" - {alias}: {fullname}")
        exit(0)

    if args.verbose and args.very_verbose:
        print("Both --verbose and --very-verbose specified, using --very-verbose.")

    global DEBUG, TIMING
    DEBUG = 0 if not args.verbose and not args.very_verbose else (2 if args.very_verbose else 1)
    TIMING = False or args.timing

    if args.number and args.bits:
        print("Error: --number and --bits are mutually exclusive.", file=sys.stderr)
        sys.exit(1)
    if args.number or args.bits:
        kwags = {}
        if args.num_jobs:
            kwags["num_jobs"] = args.num_jobs
        if args.num_parallel_jobs:
            kwags["num_parallel_jobs"] = args.num_parallel_jobs
        if args.retries:
            kwags["retries"] = args.retries
        if args.retry_factor:
            kwags["retry_factor"] = args.retry_factor
        if args.parallelization_variant:
            kwags["multivariant"] = args.parallelization_variant
        N = None
        bits = None
        if args.number is not None:
            N = args.number
        elif args.bits is not None:
            bits = args.bits
            if 6 < bits < 150:
                pass  # reasonable
            elif 150 <= bits <= 4096:
                print(f"Warning! {bits} bits are a lot. This computation may never complete!", file=sys.stderr)
            else:
                print("Error: --bits must be at least 7, and not too large.", file=sys.stderr)
                sys.exit(1)
        testQuadraticSieve(variant_func=globals()[f"{args.module}_QS"], N=N, bits=bits, debug=DEBUG, timing=TIMING, **kwags)
    else:
        print("Error: One of --number or --bits must be specified.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    print("Run this file with ../run.py!")
    sys.exit(1)