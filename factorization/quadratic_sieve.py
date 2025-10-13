import numpy as np

def quadratic_sieve(N: int):
    """
    Quadratic Sieve algorithm (simplified pseudocode)
    Input:  N (composite integer)
    Output: a nontrivial factor of N

    Pseudocode author: ChatGPT.
    """

    # <IMPLEMENT STEPS 1, 2 and 3>
    relations = list[tuple[int, list[int]]]
    relations = []
    factor_base = list[int]
    factor_base = []
    B = int
    B = -1
    # </IMPLEMENT STEPS>

    # IOANNA: I am assuming that relations have the structure
    # [(x1, [e11, e12, e13, ...]), ...]
    # where [eij] is the exponents of the prime factors of Q(x_i)
    # and factor_base is the list of primes [p1, p2, p3, ...],
    # of length B.
    # Feel free to refactor step 4 as needed!

    # 4. Build A, the exponent matrix mod 2
    A = np.array([exponents for _, exponents in relations], dtype=int)
    A = (A % 2).astype(bool)

    # 5. Find left nullspace basis vectors
    # i.e. linear dependencies mod 2
    # i.e. e such that eA = 0 (mod 2)
    # i.e. subsets of relations whose Q(x)
    #   multiply to a square, Y²
    nullspace_basis_vectors = find_left_nullspace_basis_vectors(A)

    # 6. Try basis vectors until a nontrivial factor is found
    for vec in nullspace_basis_vectors:
        # Compute X and Y from the subset of relations
        X = 1
        Y2_exponents = np.zeros(B, dtype=int)  # exponent vector for Y²
        for i, bit in enumerate(vec):
            if bit:
                x_i, factors_i = relations[i]
                X = (X * x_i) % N
                Y2_exponents += factors_i
        
        # Y² = ∏ p_j^(e_j) where e_j are even
        # so Y = ∏ p_j^(e_j/2)
        Y_exponents = Y2_exponents // 2

        Y = 1
        for j, exp in enumerate(Y_exponents):
            Y = (Y * pow(factor_base[j], exp, N)) % N

        # 7. Compute gcd(X - Y, N)
        # and test for nontrivial factor
        g = np.gcd(X - Y, N)
        if 1 < g < N:
            return g
        else:
            continue # try next basis vector
    else:
        raise ValueError("Failed to find a nontrivial factor; try increasing B.")

def find_left_nullspace_basis_vectors(
    A: np.ndarray
    ) -> list[np.ndarray]:
    """
    Find a basis for the nullspace of the given binary matrix mod 2.
    
    :param mtx np.ndarray: binary exponent matrix (mod 2)
    :return list[np.ndarray]: list of nullspace basis vectors
    """
    # We want the left nullspace of A,
    # i.e. to find basis vectors e such that eA = 0 (mod 2).
    # since A is given as rows of relations Q(x),
    # and ordinary RREF finds the right nullspace.
    A = A.transpose()


    # Perform Gaussian elimination mod 2 to get RREF
    R, pivot_cols = rref_gf2(A)
    n_rows, n_cols = R.shape

    # Identify non-pivot (free) columns
    free_cols = []
    i = 0
    for j in range(n_cols):
        if i >= n_rows or j < pivot_cols[i]:
            free_cols.append(j)
        else:
            i += 1
    
    # Construct nullspace basis vectors
    basis = []
    for x_f in free_cols:
        # Each free column gives one 
        # basis vector of the nullspace
        vec = np.zeros(n_cols, dtype=int)
        """
        fix x_f = 1 for free_col,
        x_j = 0 for other free columns.
        Then, include x_i in the basis vector
        if R[i, free_col] == 1,
        that is, if x_f appears in the equation for x_i.
        Note that x_i lives at pivot_cols[i].
        """

        vec[x_f] = 1
        for i in range(n_rows):
            if R[i, x_f] == 1:
                x_i  =  pivot_cols[i]
                vec[x_i] = 1
        basis.append(vec)

    return basis

def rref_gf2(
        A: np.ndarray
        ) -> np.ndarray:
    """Gaussian elimination mod 2 to convert A into RREF form.

    RREF - Reduced Row Echelon Form. 
    
    :param mtx np.ndarray: binary exponent matrix (mod 2)
    :return np.ndarray: RREF form of the input matrix
    """

    A = A.copy()  # don't modify input
    
    n_rows, n_cols = A.shape

    pivot_row = 0
    pivot_cols = [-1] * n_rows
    for j in range(n_cols):
        # find a row (pivot prime) that includes Q(x)
        for i in range(pivot_row, n_rows):
            if A[i, j] == 1: break
        else: continue # Q(x) is already reduced

        # Swap pivot_row and i, to put into row echelon form.
        # This does not change the nullspace of A,
        # because we are just reordering prime composition,
        # not changing the location of Q(x)
        # (which are currently columns of A).
        
        A[[pivot_row, i]] = A[[i, pivot_row]]
        pivot_cols[i] = j # pivot i found in column j

        # eliminate Q(x) from all other rows
        for i in range(n_rows):
            if i != pivot_row and A[i, j] == 1:
                A[i] ^= A[pivot_row]  # XOR operation (mod 2 addition)
        
        pivot_row += 1
    
    return A, pivot_cols