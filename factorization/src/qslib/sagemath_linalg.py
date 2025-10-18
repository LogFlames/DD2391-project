"""Written with LLM assistance."""

from sage.all import Matrix, GF
import numpy as np

####################################################
# Improvement of Step 5: Finding sum(Q(x_i)) = Y^2 #
# --------------- Using external library: SageMath # 
####################################################

def find_left_nullspace_basis_vectors_sage(
    A: np.ndarray,
    ) -> list[np.ndarray]:
    """
    Use SageMath to find all left nullspace basis vectors mod 2 in the given binary matrix.

    :param mtx np.ndarray: binary exponent matrix (mod 2)
    :return list[np.ndarray]: list of nullspace basis vectors
    """
    A = A.astype(np.uint8) # Compliance with SageMath

    # Build a matrix over GF(2)
    S = Matrix(GF(2), A)
    
    # Compute left nullspace basis vectors
    nullspace = S.left_kernel(basis='pivot') # makes output look like our native implementation
    nullspace_basis_vectors = nullspace.basis()

    # Return basis vectors
    basis = []
    for v in nullspace_basis_vectors:
        basis.append(np.array(list(v), dtype=int))
    return basis

###########################
# QS with SageMath linalg #
###########################

import src.qslib.base as base
import src.qslib.np_sieving as np_sieving
from typing import Literal

def quadratic_sieve(N: int, B: int|Literal["auto"]="auto"):
    """Like base.quadratic_sieve, but using numpy-accelerated sieving and SageMath linalg."""
    B, M = base.select_parameters(N, B)
    print(f"\nB = {int(B)}\n")
    factor_base = base.build_factor_base(N, B)
    probable_smooth = np_sieving.sieving(N, factor_base, M)
    relations = base.filter_and_find_exponents(probable_smooth, factor_base)
    nullspace_basis_vectors = base.find_sets_of_squares(relations)
    factor = base.test_found_subsets(N, factor_base, relations, nullspace_basis_vectors)

    if factor != -1:
        # Successful factorization
        return factor
    else:
        raise ValueError("Failed to find a nontrivial factor of N, try increasing B.")