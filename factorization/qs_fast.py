import numpy as np # effective array operations
import math
from numba import njit
from sympy import sqrt_mod, isprime
from typing import Literal

# Progress bars
from tqdm import tqdm
import tqdm.contrib.concurrent

# Used for sieving operations, slightly faster than Python's built-in
import gmpy2

"""def print(A):
    tqdm.write(str(A))
"""
def euler_criterion(N, p):
    """
    Checks if N is a quadratic residue module p using Euler's Criterion.
    (i.e., evaluating whether the Legendre symbol (N/p) is 1.)
    
    Euler's criterion: (n/p) ≡ n^((p-1)/2) (mod p)
    
    If the result is 1, then n is a quadratic residue mod p.
    """
    if p == 2:      # Euler's criterion doesn't work for 2 because it's not an odd number
        return N % 2 == 1
    elif N % p == 0:
        return True
    else:
        return pow(N, (p-1)//2, p) == 1    # pow(base, exp, mod)

def find_exponents(probable_smooth, factor_base):
    """
    Given probable smooth (x, y) pairs, return a list of (x, [exponents]) where
    exponents[i] = exponent of factor_base[i] in the factorization of y = x^2 - N.
    
    (Only returns relations that are completely factored over the factor base.
    It uses trial division - only for the probable smooth numbers we found before.)
    """

    results = []

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
                # fill remaining primes with zeros and break early
                exponents += [0] * (len(factor_base) - len(exponents))
                break

        if value == 1:  # x is indeed a B-smooth number
            results.append((x, exponents))

    return results

def sieving(N, factor_base, M, num_threads, variant: Literal["multiprocessing", "multithreading"]="multithreading"):
    """
    Perform the sieving step of the Quadratic Sieve algorithm in parallel.
    
    :param N: The integer to be factored.
    :param factor_base: List of primes in the factor base.
    :param M: The interval parameter defining the range [-M, M].
    :param num_threads: Number of threads to use for parallel sieving, or 1 for single-core sieving.
    :return: List of tuples (x, Q(x)) where Q(x) is B-smooth.
    """
    factor_base = np.array(factor_base) # ensure numpy array for efficiency

    if num_threads < 1:
        raise ValueError("num_threads must be at least 1")
    if num_threads == 1:
        factor_base_roots = [
                np.array(sqrt_mod(N, p, all_roots=True), dtype=object)
                if sqrt_mod(N, p, all_roots=True)
                else np.array([], dtype=object) for p in factor_base
                ]

        probable_smooth = _sieve_worker(
            N,
            math.isqrt(N),
            factor_base,
            factor_base_roots,
            M,
            -M,
            M+1
        )
        probable_smooth = list(map(tuple, probable_smooth))
    else:
        probable_smooth = parallel_sieving(N, factor_base, M, num_threads, variant)
    return probable_smooth

def parallel_sieving(N, factor_base, M, num_threads, variant):
    probable_smooth = set()
    sqrt_N = math.isqrt(N)

    # Precompute roots for each prime
    factor_base_roots = []
    for p in factor_base:
        roots = sqrt_mod(N, p, all_roots=True)
        if roots:
            factor_base_roots.append(np.array([gmpy2.mpz(r) for r in roots], dtype=object))
        else:
            factor_base_roots.append(np.array([], dtype=object))

    # Compute only chunk bounds, pass chunk generation to _sieve_worker
    interval_min = -M
    interval_max = M+1
    interval_len = interval_max - interval_min

    chunk_size = interval_len // num_threads
    bounds = [
        (i*chunk_size, (i+1)*chunk_size if i != num_threads-1 else interval_len)
        for i in range(num_threads)
    ]

    if variant == "multiprocessing":
        import os
        cpus = min(os.cpu_count(), num_threads)
        mapper = lambda f, *args, **kwargs: tqdm.contrib.concurrent.process_map(f, *args, **kwargs, max_workers=cpus)
    elif variant == "multithreading":
        mapper = lambda f, *args, **kwargs: tqdm.contrib.concurrent.thread_map(f, *args, **kwargs, max_workers=num_threads)
    else: raise ValueError("variant must be 'multiprocessing' or 'multithreading'")
    inputs = [
        (N, sqrt_N, factor_base, factor_base_roots, M, interval_min + start, interval_min + end)
        for start, end in bounds
    ]
    results = mapper(_sieve_worker_controller, inputs)
    for res in results:
        probable_smooth.update(res)

    probable_smooth = list(probable_smooth)
    return probable_smooth

def _sieve_worker_controller(args):
    # Multiprocessing-compatible controller
    return _sieve_worker(*args)

def _sieve_worker(N, sqrt_N, factor_base, factor_base_roots, M, start, end):

    # Use numpy for efficient array operations + gmpy2 for big integers
    interval = np.arange(gmpy2.mpz(start), gmpy2.mpz(end), dtype=object)
    x_vals = sqrt_N + interval
    Qx = x_vals**2 - N
    Qx_int = np.array([int(q) for q in Qx]) # compatibility with np.log
    sieve_array = np.log(np.abs(Qx_int))  # start with log|Q(x)|

    for i in tqdm.tqdm(range(len(factor_base)), leave=True): # tqdm adds progress bar
        p = factor_base[i]
        roots = factor_base_roots[i]

        for r in roots: # won't run if roots is empty
            if r == -1: break # sentinel for unused entries
            r = gmpy2.mpz(r)
            power = gmpy2.mpz(p)
            while power <= 2 * M:
                # Find indices where (x mod power) == (r mod power)
                indices = np.where((x_vals % power) == (r % power))[0]
                sieve_array[indices] -= np.log(p)
                power *= gmpy2.mpz(p)

    # Find indices where sieve_array < 0.5
    smooth_indices = np.where(sieve_array < 0.5)[0]
    x_smooth = x_vals[smooth_indices]
    y_smooth = Qx[smooth_indices]

    # Return as set of tuples
    probable_smooth = set(zip(x_smooth, y_smooth))
    return probable_smooth

def find_left_nullspace_basis_vectors(
    A: np.ndarray,
    ) -> list[np.ndarray]:
    from sage.all import Matrix, GF
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

perf_time_array: list[(str, float)]

def get_timing() -> list[(str, float)]:
    global perf_time_array
    return perf_time_array

def print_timing(include_debug=False):
    global perf_time_array
    init_t = perf_time_array[0][1]
    prev_t = init_t
    print("\nTiming:")
    for s, t in perf_time_array:
        if not include_debug and ("DEBUG" in s or s == "init"):
            continue
        print(f"{s}: {t-prev_t:.3f} s, total: {t - init_t:.3f} s")
        prev_t = t
    print()

def quadratic_sieve(
        N: int,
        B: int|str="auto",
        threads: int=1,
        DEBUG: int=0,
        TIMING: bool=False,
        RETRIES: int=0,
        MULTIVARIANT: Literal["multiprocessing", "multithreading"]="multithreading"
        ) -> int:
    """
    Quadratic Sieve algorithm
    Input:  N (composite integer)
    Output: a nontrivial factor of N

    Pseudocode author: ChatGPT.
    Code authors: Venetia Ioanna Papadopoulou and Eskil Nyberg
    """

    if TIMING: import time; global perf_time_array; perf_time_array = []; perf_time_array.append(("init", time.perf_counter()))

    # 1. Parameter selection (B and M)

    # B controls the size of the factor base.
    if B == "auto":
        B = math.exp(0.5 * math.sqrt(math.log(N) * math.log(math.log(N))))
        if N < 10**15:
            B = max(B, 100)   # minimum B for small N
    elif type(B) == str:
        raise ValueError("B must be an integer or 'auto'")

    # M defines the interval [-M, M] around sqrt(N) where we search for B-smooth numbers
    M = int(pow(B, 2))

    if TIMING: perf_time_array.append(("1", time.perf_counter()))

    # 2. Build the factor base of small primes.
    # It contains only primes p where N is a quadratic residue mod p.
    factor_base = np.array([], dtype=np.int64)
    for p in range(2, int(B)+1):
        if isprime(p) and euler_criterion(N, p) == True:
            factor_base = np.append(factor_base, p)

    if TIMING: perf_time_array.append(("2", time.perf_counter()))
    if DEBUG > 0:
        print("\nParameters:")
        print(f"- B: {int(B)+1}\n- M: {M}\n- Size of factor base: {len(factor_base)}")
        if DEBUG > 1: print("Factor base:", factor_base)
        print("\nSieving...")
        if TIMING: perf_time_array.append(("2.DEBUG", time.perf_counter()))

    # 3. Find probable B-smooth numbers
    probable_smooth = sieving(N, factor_base, M, num_threads=threads, variant=MULTIVARIANT)

    if TIMING: perf_time_array.append(("3", time.perf_counter()))
    if DEBUG > 0:
        print(f"Number of probable smooth numbers found: {len(probable_smooth)}")
        if DEBUG > 1:
            print("\nProbable smooth numbers (x, Q(x)):")
            for x, y in probable_smooth:
                print(f"x={x}, Q(x)={y}")
        print("\nVerifying smoothness and finding exponents...")
        if TIMING: perf_time_array.append(("3.DEBUG", time.perf_counter()))

    # 4 pt 1. Find the exponents
    relations = find_exponents(probable_smooth, factor_base)
    relations = [(x, exp) for x, exp in relations if x > 0]

    if TIMING: perf_time_array.append(("X", time.perf_counter()))
    if DEBUG > 0:
        print(f"Number of relations (fully factored over the factor base): {len(relations)}")
        if DEBUG > 1:
            print("\nRelations with full factorization over the factor base:")
            for x, exponents in relations:
                print(f"x={x}, exponents={exponents}")
        print("\nBuilding A...")
        if TIMING: perf_time_array.append(("X.DEBUG", time.perf_counter()))

    # 4 pt 2. Build A, the exponent matrix mod 2
    A = np.array([exponents for _, exponents in relations], dtype=int)
    A = (A % 2).astype(bool)

    if TIMING: perf_time_array.append(("4", time.perf_counter()))
    if DEBUG > 0:
        print(f"Shape of exponent matrix A: {A.shape}")
        if DEBUG > 1:
            print("\nExponent matrix A (mod 2):")
            print(A.astype(int))
        print("\nFinding left nullspace basis vectors...")
        if TIMING: perf_time_array.append(("4.DEBUG", time.perf_counter()))

    # 5. Find left nullspace basis vectors
    # i.e. linear dependencies mod 2
    # i.e. e such that eA = 0 (mod 2)
    # i.e. subsets of relations whose Q(x)
    #   multiply to a square, Y²
    nullspace_basis_vectors = find_left_nullspace_basis_vectors(A)

    if TIMING: perf_time_array.append(("5", time.perf_counter()))
    if DEBUG > 0:
        print("Left nullspace basis vectors:")
        print(f"- Number of basis vectors: {len(nullspace_basis_vectors)}")
        print(f"- Shape of basis vectors: {nullspace_basis_vectors[0].shape if nullspace_basis_vectors else 'N/A'}")
        if DEBUG > 1:
            for vec in nullspace_basis_vectors:
                print(vec)
        print("\nTrying basis vectors to find a nontrivial factor...")
        if TIMING: perf_time_array.append(("5.DEBUG", time.perf_counter()))
    
    # 6. Try basis vectors until a nontrivial factor is found
    if DEBUG: runs = 1
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

        Y = 1
        for j, exp in enumerate(Y_exponents):
            Y = (Y * pow(int(factor_base[j]), exp, N)) % N

        # 7. Compute gcd(X - Y, N)
        # and test for nontrivial factor
        g = np.gcd(X - Y, N)
        if 1 < g < N:
            if DEBUG: print(f"Found a nontrivial factor after {runs} basis vectors: {g}\n")
            if TIMING: perf_time_array.append(("6", time.perf_counter()))
            return g
        else:
            if DEBUG: runs += 1
            continue # try next basis vector
    else:
        if DEBUG: print(f"Tried all {len(nullspace_basis_vectors)} basis vectors, but found no nontrivial factor.\n")
        if TIMING: perf_time_array.append(("6+7.FAIL", time.perf_counter()))

        if RETRIES <= 0:
            raise ValueError("Failed to find a nontrivial factor; try increasing B.")
        else:
            if DEBUG: print(f"\n\nRetrying with increased B (attempts left: {RETRIES})...\n")
            return quadratic_sieve(N, B=int(B*1.5), threads=threads, DEBUG=DEBUG, TIMING=TIMING, RETRIES=RETRIES-1)