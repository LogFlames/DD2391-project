import numpy as np
from sage.all import Matrix, GF

def find_left_nullspace_basis_vectors_sagemath(
    A: np.ndarray,
    ) -> list[np.ndarray]:
    """
    Use SageMath to find all linear dependencies mod 2 in the given binary matrix.
    
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