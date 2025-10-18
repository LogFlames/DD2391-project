"""Written with LLM assistance."""

###################################
# Improvement for step 3: Sieving #
# -- Numpy for int64 acceleration #
###################################

import math
from sympy import sqrt_mod
import numpy as np

def sieving(N, factor_base, M):
    """Re-written with LLM assistance to maximally use numpy arrays. Only works for N < 2^63."""
    factor_base = np.array(factor_base, dtype=np.int64)
    sqrt_N = np.int64(math.isqrt(N))
    interval = np.arange(-M, M+1, dtype=np.int64)
    x_vals = sqrt_N + interval
    y_vals = x_vals**2 - N
    sieve_array = np.log(np.abs(y_vals)).astype(np.float64)

    for p in factor_base:
        roots = np.array(sqrt_mod(N, p, all_roots=True), dtype=np.int64)
        logp = np.log(p)
        for r in roots:
            indices = np.where((x_vals % p) == r)[0]
            sieve_array[indices] -= logp

    probable_indices = np.where(sieve_array < 0.5)[0]
    probable_smooth = set(zip(x_vals[probable_indices], y_vals[probable_indices]))

    return probable_smooth

######################
# QS with np sieving #
######################

import src.qslib.base as base
from typing import Literal

def quadratic_sieve(
        N: int,
        B: int|Literal["auto"]="auto",
        retries: int = 3,
        retry_factor: float = 1.2,
        ):
    """Like base.quadratic_sieve, but using numpy-accelerated sieving for N < 2^63."""
    if N >= 2**63:
        raise ValueError("This acceleration only supports N < 2^63. Use np_sieving or parallel_np_sieving instead.")
    B, M = base.select_parameters(N, B)
    print(f"\nB = {int(B)}\n")
    factor_base = base.build_factor_base(N, B)
    probable_smooth = sieving(N, factor_base, M)
    relations = base.filter_and_find_exponents(probable_smooth, factor_base)
    nullspace_basis_vectors = base.find_sets_of_squares(relations)
    factor = base.test_found_subsets(N, factor_base, relations, nullspace_basis_vectors)

    if factor != -1:
        return factor
    else:
        if retries <= 0: raise ValueError("Failed to find a nontrivial factor, try increasing B.")
        else: return quadratic_sieve(
            N,
            B=int(B*retry_factor),
            retries=retries-1,
            retry_factor=retry_factor
            )