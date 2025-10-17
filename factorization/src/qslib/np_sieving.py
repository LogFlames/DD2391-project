###################################
# Improvement for step 3: Sieving #
# -- Using Numpy for acceleration #
###################################

import math
from sympy import sqrt_mod
import numpy as np

def sieving(N, factor_base, M):
    sqrt_N = math.isqrt(N)
    interval = range(-M, M+1)
    probable_smooth = set()

    sieve_array = [math.log(abs((sqrt_N + x)**2 - N)) for x in interval]
    sieve_array = np.array(sieve_array) # NUMPY IMPROVEMENT

    for p in factor_base:
        roots = sqrt_mod(N, p, all_roots=True)

        for r in roots:
            power = p

            while power <= 2*M:
                offset = ((sqrt_N + interval[0]) - r) % power
                if offset != 0:
                    offset = power - offset
                for i in range(offset, len(interval), power):
                    sieve_array[i] -= np.log(p) # NUMPY IMPROVEMENT
                power *= p

        for i in np.where(sieve_array < 0.5)[0]:
            x = sqrt_N + interval[i]
            y = pow(x, 2) - N
            probable_smooth.add((x, y))

    return probable_smooth

######################
# QS with np sieving #
######################

import src.qslib.base as base
from typing import Literal

def quadratic_sieve(N: int, B: int|Literal["auto"]="auto"):
    """Like base.quadratic_sieve, but using numpy-accelerated sieving."""
    B, M = base.select_parameters(N, B)
    print(f"\nB = {int(B)}\n")
    factor_base = base.build_factor_base(N, B)
    probable_smooth = sieving(N, factor_base, M)
    relations = base.filter_and_find_exponents(probable_smooth, factor_base)
    nullspace_basis_vectors = base.find_sets_of_squares(relations)
    factor = base.test_found_subsets(N, factor_base, relations, nullspace_basis_vectors)

    if factor != -1:
        # Successful factorization
        return factor
    else:
        raise ValueError("Failed to find a nontrivial factor of N, try increasing B.")
