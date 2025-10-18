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
>   max63bit    for src.qslib.np_sieving_max63bit.quadratic_sieve
>   olp         for src.qslib.one_large_prime.quadratic_sieve
>   sagemath    for src.qslib.sagemath_linalg.quadratic_sieve

---

The standard and fastest implementation is
>   src.qslib.complete.quadratic_sieve
which is a superset of the parallel_np_sieving version,
adding debug output, timing, and retry logic.

The easiest implementation to understand is
>   src.qslib.base.quadratic_sieve
which is a straightforward implementation of the Quadratic Sieve algorithm.

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
    "olp": "src.qslib.one_large_prime.quadratic_sieve",
    "sagemath": "src.qslib.sagemath_linalg.quadratic_sieve",
}

DEBUG = 0 # default, can be changed by argument
TIMING = False # default, can be changed by argument

def base_QS(N: int, B: int="auto", __internal=False, **kwargs):
    """Alias for src.qslib.base.quadratic_sieve.quadratic_sieve"""
    if kwargs: print(f"Ignoring {kwargs} for base_QS")
    import src.qslib.base
    module = src.qslib.base
    result = module.quadratic_sieve(N, B)
    return (result, module) if __internal else result

def np_QS(N: int, B: int="auto", __internal=False, **kwargs):
    """Alias for src.qslib.np_sieving.quadratic_sieve.quadratic_sieve"""
    if kwargs: print(f"Ignoring {kwargs} for np_QS")
    import src.qslib.np_sieving
    module = src.qslib.np_sieving
    result = module.quadratic_sieve(N, B)
    return (result, module) if __internal else result

def parallel_QS(N: int, B: int="auto", chunks: int=4, jobs: int=4, multivariant: Literal["multithreaded", "multiprocessing"]="multiprocessing", __internal=False, **kwargs):
    """Alias for src.qslib.parallel_np_sieving.quadratic_sieve.quadratic_sieve"""
    if kwargs: print(f"Ignoring {kwargs} for parallel_QS")
    import src.qslib.parallel_np_sieving
    module = src.qslib.parallel_np_sieving
    result = module.quadratic_sieve(N, B, chunks=chunks, jobs=jobs, multivariant=multivariant)
    return (result, module) if __internal else result

def complete_QS(N: int, B: int="auto", chunks: int=-1, jobs: int=4, retries: int=0, retry_factor: float=1.2, multivariant: Literal["multithreaded", "multiprocessing"]="multiprocessing", one_large_prime: bool=False, debug: int=0, timing: bool=TIMING, __internal=False):
    """Alias for src.qslib.complete.quadratic_sieve.quadratic_sieve"""
    import src.qslib.complete
    module = src.qslib.complete
    result = module.quadratic_sieve(N, B, chunks=chunks, jobs=jobs, retries=retries, retry_factor=retry_factor, multivariant=multivariant, one_large_prime=one_large_prime, debug=debug, timing=timing)
    return (result, module) if __internal else result

def olp_QS(N: int, B: int="auto", chunks: int=4, jobs: int=4, multivariant: Literal["multiprocessing", "multithreading"]="multiprocessing", __internal=False):
    """Alias for src.qslib.one_large_prime.quadratic_sieve.quadratic_sieve"""
    import src.qslib.one_large_prime
    module = src.qslib.one_large_prime
    result = module.quadratic_sieve(N, B, chunks=chunks, jobs=jobs, multivariant=multivariant)
    return (result, module) if __internal else result

def sagemath_QS(N: int, B: int="auto", __internal=False, **kwargs):
    """Alias for src.qslib.sagemath_linalg.quadratic_sieve.quadratic_sieve"""
    if kwargs: print(f"Ignoring {kwargs} for sagemath_QS")
    import src.qslib.sagemath_linalg
    module = src.qslib.sagemath_linalg
    result = module.quadratic_sieve(N, B)
    return (result, module) if __internal else result

def testQS(variant_func,
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
    
    try:
        factor, module = variant_func(N, __internal=True, **kwargs)
    except ValueError:
        print("Factorization failed! Try increasing B.")
        return
    if timing and module.__name__ == "src.qslib.complete":
        module.print_timing()
    print(f"Returned factor: {factor}")
    assert N % factor == 0 and factor != 1 and factor != N
    print("Test passed!")

def getComposite(bits: int):
    import Crypto.Util.number as number

    _validate_bits(bits)

    p = number.getPrime(bits//2)
    q = number.getPrime(bits//2 + (1 if bits % 2 else 0))
    N = p * q
    print(f"Generated {bits}-bit / {len(str(N))}-digit composite\n| {N} = \n| {p} \n|  * \n| {q}")
    return N

def _validate_bits(bits: int):
    if 6 < bits < 150:
        pass  # reasonable
    elif 150 <= bits <= 4096:
        print(f"Warning! {bits} bits are a lot. This computation may never complete!", file=sys.stderr)
    else:
        raise ValueError("Error: --bits must be at least 7, and not too large.")
def _main():
    import sys
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", default="factor", choices=["factor", "list_variants", "gen_composite", "repl"],
                        help="Mode to run: 'factor' to factor a number, 'list_variants' to list available variants, 'gen_composite' to generate a composite number N = p*q, or 'repl' to start a Python REPL. Most optional arguments only apply to the 'factor' mode.")
    parser.add_argument("-M", "--module", default="complete", type=str, choices=list(aliases.keys()),
                        help="Module (Quadratic Sieve variant) to use.")
    parser.add_argument("-b", "--bits", type=int, default=None,
                        help="Number of bits of the composite number to generate and factor (incompatible with --number).")
    parser.add_argument("-n", "-N", "--number", type=int, default=None,
                        help="Composite number to factor (overrides --bits).")
    parser.add_argument("-B", "--B-parameter", type=int,
                        help="Manually set the B-smoothness bound.")
    parser.add_argument("-C", "--chunks", type=int,
                        help="(Only compatible with some variants.) Number of chunks to split work into, for parallel variants. Can be larger than -J")
    parser.add_argument("-J", "--jobs", type=int, default=4,
                        help="(Only compatible with some variants.) Number of jobs to run in parallel, for parallel variants.")
    parser.add_argument("-R", "--retries", type=int, default=0,
                        help="(Only compatible with some variants.) Number of retries on failure.")
    parser.add_argument("-RF", "--retry-factor", type=float, default=1.2,
                        help="(Only compatible with some variants.) Factor to increase the smoothness bound B by on each retry.")
    parser.add_argument("-PV", "--parallelization-variant", type=str, default="multiprocessing", choices=["multiprocessing", "multithreading"],
                        help="(Only compatible with some variants.) Parallelization variant to use. Recommended: multiprocessing.")
    parser.add_argument("-OLP", "--one-large-prime", action="store_true",
                        help="(Only compatible with some variants.) Use the 'one-large-prime' variant for the 'complete' module.")
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

    if args.verbose and args.very_verbose:
        print("Both --verbose and --very-verbose specified, using --very-verbose.")

    global DEBUG, TIMING
    DEBUG = 0 if not args.verbose and not args.very_verbose else (2 if args.very_verbose else 1)
    TIMING = False or args.timing

    if args.mode == "repl":
        _repl_print_info()
        import code
        code.interact(local=globals())
        return

    if args.mode == "list_variants":
        print("Available Quadratic Sieve variants:")
        for alias, fullname in aliases.items():
            print(f" - {alias}: {fullname}")
        exit(0)

    if args.mode == "gen_composite":
        if args.bits:
            getComposite(args.bits)
        else:
            print("Error: pass --bits to use this module!")
        exit(0)

    if args.number and args.bits:
        print("Error: --number and --bits are mutually exclusive.", file=sys.stderr)
        sys.exit(1)
    if args.number or args.bits:
        kwargs = {}
        if args.B_parameter:
            kwargs["B"] = args.B_parameter
        if args.chunks:
            kwargs["chunks"] = args.chunks
        if args.jobs and ("-J" in sys.argv or "--jobs" in sys.argv):
            kwargs["jobs"] = args.jobs
        if args.retries and ("-R" in sys.argv or "--retries" in sys.argv):
            kwargs["retries"] = args.retries
        if args.retry_factor and ("-R" in sys.argv or "--retries" in sys.argv):
            kwargs["retry_factor"] = args.retry_factor
        if args.parallelization_variant and ("-PV" in sys.argv or "--parallelization-variant" in sys.argv):
            kwargs["multivariant"] = args.parallelization_variant
        if args.one_large_prime:
            kwargs["one_large_prime"] = True
        N = None
        bits = None
        if args.number is not None:
            N = args.number
        elif args.bits is not None:
            bits = args.bits
            _validate_bits(bits)
        testQS(variant_func=globals()[f"{args.module}_QS"], N=N, bits=bits, debug=DEBUG, timing=TIMING, **kwargs)
    else:
        print("Error: One of --number or --bits must be specified.", file=sys.stderr)
        sys.exit(1)

def _repl_print_info():
    print("<!---")
    print("Entering REPL mode. You can now use the quadratic sieve variants directly.\nArguments other than -v, -vv and -t are discarded.")
    print("Available variants:")
    for alias in aliases.keys():
        print(f" - {alias}_QS")
    print("The following helper functions are available to you:")
    print(" - getComposite(bits: int)")
    print(" - testQS(variant_func, bits: int=None, N: int=None, **kwargs)")
    if DEBUG > 0: print(f"Default debug level set to {DEBUG}")
    if TIMING: print(f"Timing printed by default (if available)")
    print("--->\n")

if __name__ == "__main__":
    print("Loading in REPL mode. Run this file with ../run.py for command-line usage.\n")
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="(Only compatible with some variants.) Default debug level to 1.")
    parser.add_argument("-vv", "--very-verbose", action="store_true",
                        help="(Only compatible with some variants.) Default debug level to 2.")
    parser.add_argument("-t", "--timing", action="store_true",
                        help="(Only compatible with some variants.) Enable timing by default.")
    args, _ = parser.parse_known_args()
    
    DEBUG = 0 if not args.verbose and not args.very_verbose else (2 if args.very_verbose else 1)
    TIMING = False or args.timing

    _repl_print_info()
    