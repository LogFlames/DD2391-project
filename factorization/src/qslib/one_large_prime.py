"""
Implementation of the "One Large Prime" variant of the Quadratic Sieve algorithm.

This variant allows relations that are almost B-smooth, containing exactly one prime
larger than the factor base (and smaller than some "large prime bound").
These are called partial relations and later on we pair two such relations that share
the same large prime. That way we produce more full relations.
"""

######################################################
# Changes to Step 4: Filtering and finding Exponents #
# ----------- Variant of the QS: 1-Large-Prime / OLP #
######################################################

from sympy import isprime

def filter_and_find_exponents_olp(B, probable_smooth, factor_base, prime_bound: int=None):
    """
    Implements the 1-large-prime variant of the Quadratic Sieve algorithm.

    Given probable smooth (x, y) pairs, returns:
     - one list of (x, [exponents]) where exponents[i] = exponent of factor_base[i]
       in the factorization of y = x^2 - N.
     - another list of (x, [exponents], value) where value is the large prime
       number p fow which is true B < p < prime_bound

    It uses trial division - only for the probable smooth numbers we found before.
    It returns relations that are completely factored over the factor base and in addition,
    it also records partial relations that contain exactly one prime larger than the 
    factor base (but below "prime_bound").

    :param B: The bound for the factor base.
    :param probable_smooth: List of (x, y) pairs where y = x
    :param factor_base: List of primes in the factor base.
    :param prime_bound: Upper bound for the large prime in partial relations, default is 10*B.
    :return: (full_relations, partial_relations)
    """
    if not prime_bound: prime_bound = 10*B
    full_relations = []
    partial_relations = []

    for x, y in probable_smooth:
        value = abs(y)
        exponents = []

        for p in factor_base:
            exp = 0
            while value % p == 0:
                exp += 1
                value //= p
            exponents.append(exp)

            if value == 1:
                exponents += [0] * (len(factor_base) - len(exponents))
                full_relations.append((x, exponents))
                break
            elif (value < prime_bound) and isprime(value):
                partial_relations.append((x, exponents, value))

    relations = full_relations + _combine_relations(partial_relations, B)

    return relations

def _combine_relations(partial_relations, N):
    """
    Combines partial relations (into pairs) that share the same large prime number
    and turns them into full relations.
    
    Two partial relations with the same large prime can be multiplied together to
    "cancel" that prime (the exponent becomes even), producing a full B-smooth relation.

    :param partial_relations: List of (x, [exponents], large_prime) tuples.
    :param N: The integer being factored.
    :return: List of full relations (x, [exponents]).
    """
    full_relations = []
    combinations ={}    # partials by prime

    for x1, exponents1, prime in partial_relations:
        if prime in combinations:
            x2, exponents2, prime = combinations.pop(prime)
            x = (x1 * x2) % N
            exponents = [(e1 + e2) for e1, e2 in zip(exponents1, exponents2)]
            full_relations.append((x, exponents))
        else:
            combinations[prime] = (x1, exponents1, prime)

    return full_relations

#################################
# QS with 1-Large-Prime variant #
#################################

import src.qslib.base as base
import src.qslib.parallel_np_sieving as parallel_np_sieving
from typing import Literal

def quadratic_sieve(N: int, B: int|Literal["auto"]="auto", num_jobs: int=1, max_parallel_jobs: int=1, multivariant: Literal["multiprocessing", "multithreading"]="multiprocessing") -> int:
    """
    Like base.quadratic_sieve, but with numpy accelerated sieving and enabled for parallel sieving.
    
    :param N: The integer to be factored (should be a composite number).
    :param B: The bound for the factor base (or "auto" to compute automatically).
    :param num_jobs: Number of jobs to split the sieving into.
    :param max_parallel_jobs: Maximum number of parallel jobs to run concurrently.
    :param variant: "multiprocessing" or "multithreading" to choose parallelization method.
    WARNING: Multithreading is GIL-bound and will not yield speedup. Even with GIL disabled on a freethreaded version of Python, speed-up is not achieved (except maybe for quite small numbers).
    :return: A nontrivial factor of N, or raises ValueError if no factor is found.
    """
    B, M = base.select_parameters(N, B)
    print(f"\nB = {int(B)}\n")
    factor_base = base.build_factor_base(N, B)
    probable_smooth = parallel_np_sieving.parallel_sieving(N, factor_base, M, num_jobs, max_parallel_jobs, multivariant)
    relations = filter_and_find_exponents_olp(B, probable_smooth, factor_base)
    nullspace_basis_vectors = base.find_sets_of_squares(relations)
    factor = base.test_found_subsets(N, factor_base, relations, nullspace_basis_vectors)

    if factor != -1:
        # Successful factorization
        return factor
    else:
        raise ValueError("Failed to find a nontrivial factor of N, try increasing B.")