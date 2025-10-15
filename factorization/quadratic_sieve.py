import numpy as np
import math
from sympy import sqrt_mod, isprime


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

# Euler's criterion: (n/p) ≡ n^((p-1)/2) (mod p)
# If the result is 1, then n is a quadratic residue mod p.
# Checks if N is a quadratic residue modulo p.
def euler_criterion(N, p):
    if p == 2:      # Euler's criterion doesn't work for 2 because it's not an odd number
        return N % 2 == 1
    elif N % p == 0:
        return True
    else:
        return pow(N, (p-1)//2, p) == 1    # pow(base, exp, mod)

# Given probable smooth (x, y) pairs, return a list of (x, [exponents]) where
# exponents[i] = exponent of factor_base[i] in the factorization of y = x^2 - N.
# (Only returns relations that are completely factored over the factor base.
# It uses trial division - only for the probable smooth numbers we found before.)
def find_exponents(probable_smooth, factor_base):

    results = []

    for x, y in probable_smooth:
        value = abs(y)
        exponents = []

        for p in factor_base:
            # print(f"prime: {p}")
            exp = 0
            while value % p == 0:
                exp += 1
                value //= p
                # print(f"value: {value}")
            exponents.append(exp)

            if value == 1:
                # fill remaining primes with zeros and break early
                exponents += [0] * (len(factor_base) - len(exponents))
                break

        if value == 1:  # x is indeed a B-smooth number
            results.append((x, exponents))

    return results

# 3. Search for "B-smooth" Q(x) = x² - N
def sieving(N, factor_base, M):
    sqrt_N = math.isqrt(N)      # the square root of N rounded down (like: floor(sqrt(N)))
    interval = range(-M, M+1)   # range(-M, M)
    probable_smooth = set()     # a set to avoid duplicates

    # Precompute log(|Q(x)|), where Q(x) = x² - N
    # for x s.t.: -M + square_root(N) <= x < M + square_root(N)
    sieve_array = [math.log(abs((sqrt_N + x)**2 - N)) for x in interval]


    for p in factor_base:
        roots = sqrt_mod(N, p, all_roots=True)
        if not roots:
            # roots = []
            continue
        
        for r in roots:
            power = p

            #if p^k divides Q(x), we subtract (k × log(p)) total
            while power <= 2*M:
            # compute the first index of x where x ≡ r (mod p)
                offset = ((sqrt_N + interval[0]) - r) % power
                if offset != 0:
                    offset = power - offset
                # Go through the array of log(|Q(x)|) values and subtract log(p)
                # from every such value that corresponds to a Q(x) that is divisible by p.
                # for every x s.t. x ≡ r (mod p), subtract log(p) from its corresponding log(|Q(x)|)
                for i in range(offset, len(interval), power):
                    sieve_array[i] -= math.log(p)
                power *= p

        # Every time a prime p from the factor base reduces sieve_array[i] below 0.5, we append (x, y).
        # If multiple primes contribute to the same x, we append the same x multiple times.
        for i in range(len(sieve_array)):
            if sieve_array[i] < 0.5:
                x = sqrt_N + interval[i]
                y = pow(x, 2) - N
                probable_smooth.add((x,y))

    # To avoid duplicates in probable_smooth we first made it a set, and then convert it to a list
    probable_smooth = list(probable_smooth)

    return probable_smooth


def quadratic_sieve(N: int):
    """
    Quadratic Sieve algorithm (simplified pseudocode)
    Input:  N (composite integer)
    Output: a nontrivial factor of N

    Pseudocode author: ChatGPT.
    """

    # 1. Choose B using a heuristic formula.
    # B controls the size of the factor base.
    # B = math.exp(0.5 * math.sqrt(math.log(N) * math.log(math.log(N))))
    B = 50

    # M defines the interval [-M, M] around sqrt(N) where we search for B-smooth numbers
    M = int(pow(B, 2))

    # 2. Build the factor base of small primes.
    # It contains only primes p where N is a quadratic residue mod p.
    factor_base = []
    for p in range(2, int(B)+1):
        if isprime(p) and euler_criterion(N, p) == True:
            factor_base.append(p)

    print("Factor base:", factor_base)
    print("B:", B, "M:", M)

    # 3. Find probable B-smooth numbers
    probable_smooth = sieving(N, factor_base, M)

    print("\nProbable smooth numbers (x, Q(x)):")
    for x, y in probable_smooth:
        print(f"x={x}, Q(x)={y}")

    # 4. Build the exponents matrix
    relations = find_exponents(probable_smooth, factor_base)
    relations = [(x, exp) for x, exp in relations if x > 0]

    print("\nRelations with full factorization over the factor base:")
    for x, exponents in relations:
        print(f"x={x}, exponents={exponents}")

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
        Y2_exponents = np.zeros(len(factor_base), dtype=int)  # exponent vector for Y²
        for i, bit in enumerate(vec):
            if bit:
                x_i, factors_i = relations[i]
                X = (X * x_i) % N
                Y2_exponents += factors_i
        
        # Y² = ∏ p_j^(e_j) where e_j are even
        # so Y = ∏ p_j^(e_j/2)
        Y_exponents = [int(e) for e in (Y2_exponents // 2)]
        # Y_exponents = Y2_exponents // 2

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


# Prime number to be factored
N = 227179   # small test number

factor = quadratic_sieve(N)
print(f"factor: {factor}")