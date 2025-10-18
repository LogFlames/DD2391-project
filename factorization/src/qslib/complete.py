"""
This file adds debug information, timing capabilities, access to optional variants, and progress bars.
Its functionality is otherwise equivalent to parallel_np_sieving.py
"""

import src.qslib.base as base
import src.qslib.one_large_prime as olp
from typing import Literal

import math
import numpy as np
from sympy import sqrt_mod

import tqdm # Progress bars

from os import cpu_count

#############################
# Step 3: Sieving with tqdm #
#############################

def parallel_sieving(N, factor_base, M,
        chunks=1,
        jobs=1,
        variant: Literal["multiprocessing", "multithreading"]="multiprocessing"
        ):
    """
    Perform the sieving step of the Quadratic Sieve algorithm in parallel.

    Will only parallelize if num_jobs > 1 and max_parallel_jobs > 1.
    
    :param N: The integer to be factored.
    :param factor_base: List of primes in the factor base.
    :param M: The sieving interval parameter.
    :param chunks: The number of chunks to divide the work into.
    :param jobs: The number of parallel jobs to run.
    :param variant: "multiprocessing" or "multithreading" to choose parallelization method.
    WARNING: Multithreading is GIL-bound and will not yield speedup. Even with GIL disabled on a freethreaded version of Python, speed-up is not achieved (except maybe for quite small numbers).
    :return: List of tuples (x, Q(x)) where Q(x) is B-smooth.
    """
    factor_base = np.array(factor_base) # ensure numpy array for efficiency

    if chunks == -1:
        # autocalculate reasonable number
        opcount_per_chunk = 10**9
        ops = len(factor_base)*M
        chunks = int(ops/opcount_per_chunk)
        chunks = max(4, chunks)
        print(f"Chunks set to -1, using {chunks} chunks")

    if chunks < 1:
        raise ValueError("num_jobs must be at least 1")
    elif chunks > 1:
        probable_smooth = _parallel_sieving(N, factor_base, M, chunks, jobs, variant)
    else:   # single-core sieving
        factor_base_roots = [
            np.array(sqrt_mod(N, p, all_roots=True), dtype=object)
            if sqrt_mod(N, p, all_roots=True)
            else np.array([], dtype=object) for p in factor_base
            ]
        
        pbar = tqdm.tqdm(total=len(factor_base), desc="Sieving")

        probable_smooth = _sieve_worker(N, math.isqrt(N), factor_base, factor_base_roots, M, -M, M+1, pbar)
        probable_smooth = list(map(tuple, probable_smooth))
    return probable_smooth

def _parallel_sieving(N, factor_base, M, chunks, jobs, variant):
    """See parallel_np_sieving._parallel_sieving for comments."""
    probable_smooth = set()
    sqrt_N = math.isqrt(N)

    factor_base_roots = [
        np.array(sqrt_mod(N, p, all_roots=True), dtype=object)
        if sqrt_mod(N, p, all_roots=True)
        else np.array([], dtype=object) for p in factor_base
        ]

    interval_min, interval_max = -M, M+1
    interval_len = interval_max - interval_min

    chunk_size = interval_len // chunks
    bounds = [
        (i*chunk_size, (i+1)*chunk_size if i != chunks-1 else interval_len)
        for i in range(chunks)
    ]

    # only multithreading is compatible with passing tqdm process bars
    pbar = tqdm.tqdm(
        total=len(factor_base)*chunks,
        desc="Sieving",
        smoothing=0
        ) if variant == "multithreading" else None
    
    inputs = [
        (N, sqrt_N, factor_base, factor_base_roots, M, interval_min + start, interval_min + end, pbar)
        for start, end in bounds
    ]
    
    if variant == "multiprocessing":
        import multiprocessing.pool

        with multiprocessing.pool.Pool(processes=jobs) as pool:
            results = list(tqdm.tqdm(pool.imap(sieve_worker_controller, inputs), total=len(inputs), desc="Sieving (chunks)"))
    elif variant == "multithreading":
        import concurrent.futures as futures

        with futures.ThreadPoolExecutor(max_workers=jobs) as executor:
            results = list(tqdm.tqdm(executor.map(sieve_worker_controller, inputs), total=len(inputs), desc="Sieving (chunks)"))
    else: raise ValueError("variant must be 'multiprocessing' or 'multithreading'")
    
    for res in results:
        probable_smooth.update(res)
    
    probable_smooth = list(probable_smooth)
    return probable_smooth

def sieve_worker_controller(args):
    """Multi-processing compatible helper."""
    return _sieve_worker(*args)

def _sieve_worker(N, sqrt_N, factor_base, factor_base_roots, M, start, end, pbar=None):
    """See base.sieving for comments."""

    interval = range(start, end)
    probable_smooth = set()
    
    sieve_array = np.zeros(len(interval), dtype=np.float64)
    for i, x in enumerate(interval):
        sieve_array[i] = np.float64(math.log(abs((sqrt_N + x)**2 - N)))

    for j in range(len(factor_base)):
        p = int(factor_base[j])
        roots = factor_base_roots[j]
        if pbar: pbar.update(1)

        for r in roots:
            power = p

            while power <= 2*M:
                offset = ((sqrt_N + interval[0]) - r) % power
                if offset != 0:
                    offset = power - offset
                indices = np.arange(offset, len(interval), power)
                sieve_array[indices] -= np.log(p)
                power *= p

        for i in np.where(sieve_array < 0.5)[0]:
            x = sqrt_N + interval[i]
            y = pow(x, 2) - N
            probable_smooth.add((x, y))

    return probable_smooth

############################
# Step 5: Linalg with tqdm #
############################

def find_left_nullspace_basis_vectors(A: np.ndarray) -> list[np.ndarray]:
    """See base.find_left_nullspace_basis_vectors for comments."""
    A_T = A.transpose()

    R, pivot_cols = rref_gf2(A_T)
    n_rows, n_cols = R.shape

    free_cols = [j for j in range(n_cols) if j not in pivot_cols]
    if len(free_cols) == 0:
        return []
    
    basis = []
    for x_f in tqdm.tqdm(free_cols, desc="Basis vectors   "):
        vec = np.zeros(n_cols, dtype=int)

        vec[x_f] = 1
        for i in range(n_rows):
            if R[i, x_f] == 1:
                x_i = pivot_cols[i]
                vec[x_i] = 1
        basis.append(vec)

    return basis

def rref_gf2(A: np.ndarray) -> np.ndarray:
    """See base.rref_gf2 for comments."""

    A = A.copy()
    
    n_rows, n_cols = A.shape

    pivot_row = 0
    pivot_cols = [-1] * n_rows
    for j in tqdm.tqdm(range(n_cols), desc="RREF            "):
        for i in range(pivot_row, n_rows):
            if A[i, j] == 1: break
        else: continue
        
        A[[pivot_row, i]] = A[[i, pivot_row]]
        pivot_cols[pivot_row] = j 

        for i in range(n_rows):
            if i != pivot_row and A[i, j] == 1:
                A[i] ^= A[pivot_row]
        
        pivot_row += 1
    
    return A, pivot_cols


###############################################
# Complete QS with tqdm and debug information #
###############################################

perf_time_array: list[(str, float)]

def get_timing() -> list[(str, float)]:
    global perf_time_array
    return perf_time_array

def print_timing(verbosity: Literal[0, 1, 2]=0):
    """Print recorded timing information."""
    global perf_time_array
    init_t = perf_time_array[0][1]
    prev_t = init_t
    print("\nTiming:")
    for s, t in perf_time_array:
        if verbosity < 2 and ("debug" in s or s == "init"):
            continue
        if verbosity == 0:
            if (s != "3" and s != "5") and (t-prev_t) < 1: continue
            if s == "1": desc   = "Prep.           "
            elif s == "2": desc = "Factor base gen."
            elif s == "3": desc = "Sieving         "
            elif s == "4": desc = "Collection      "
            elif s == "5": desc = "Linear algebra  "
            elif s == "6": desc = "Subset testing  "
            print(f"{desc}: {t-prev_t:.3f} s")
        else:
            print(f"{s}: {t-prev_t:.3f} s, total: {t - init_t:.3f} s")
        
        prev_t = t
    if verbosity == 0: print(f"Total time taken: {t - init_t:.3f} s\n(excluding retries)")
    print()

def quadratic_sieve(
        N: int,
        B: int|str="auto",
        chunks: int=-1,
        jobs: int=min(4, cpu_count()),
        retries: int=0,
        retry_factor: float=1.2,
        multivariant: Literal["multiprocessing", "multithreading"]="multiprocessing",
        debug: int=0,
        timing: bool=False,
        one_large_prime: bool=False
        ) -> int:
    """
    Quadratic Sieve algorithm

    Code authors: Venetia Ioanna Papadopoulou and Eskil Nyberg.

    :param N: The integer to be factored (should be a composite number).
    :param B: The bound for the factor base (or "auto" to compute automatically).
    :param chunks: The number of chunks to divide the work into. This variant also accepts -1 to autocalculate this number.
    :param jobs: The number of parallel jobs to run.
    :param debug: Level of debug information (0: none, 1: basic, 2: detailed).
    :param timing: Whether to record timing information.
    :param retries: Number of retries with increased B if no factor is found.
    :param retry_factor: Factor by which to increase B on each retry.
    :param multivariant: "multiprocessing" or "multithreading" to choose parallelization method.
    :param one_large_prime: Whether to use the one_large_prime variant for the collection step.
    WARNING: Multithreading is GIL-bound and will not yield speedup. Even with GIL disabled on a freethreaded version of Python, speed-up is not achieved (except maybe for quite small numbers).
    :return: A nontrivial factor of N, or raises ValueError if no factor is found.
    """

    if timing: import time; global perf_time_array; perf_time_array = []; perf_time_array.append(("init", time.perf_counter()))

    ### 1 ###
    B, M = base.select_parameters(N, B)
    if debug == 0: print(f"\nB = {int(B)}\n")

    if timing: perf_time_array.append(("1", time.perf_counter()))

    ### 2 ###
    factor_base = base.build_factor_base(N, B)

    if timing: perf_time_array.append(("2", time.perf_counter()))
    if debug > 0:
        print("\nParameters:")
        print(f"- B: {int(B)+1}\n- M: {M}\n- Size of factor base: {len(factor_base)}")
        if debug > 1: print("Factor base:", factor_base)
        print("\nSieving...")
        if timing: perf_time_array.append(("debug", time.perf_counter()))

    ### 3 ###
    probable_smooth = parallel_sieving(N, factor_base, M, chunks, jobs, multivariant)

    if timing: perf_time_array.append(("3", time.perf_counter()))
    if debug > 0:
        print(f"Number of probable smooth numbers found: {len(probable_smooth)}")
        if debug > 1:
            print("\nProbable smooth numbers (x, Q(x)):")
            for x, y in probable_smooth:
                print(f"x={x}, Q(x)={y}")
        print("\nVerifying smoothness and finding exponents...")
        if timing: perf_time_array.append(("debug", time.perf_counter()))

    ### 4 ###
    if one_large_prime:
        relations, factor_base = olp.filter_and_find_exponents_olp(N, B, probable_smooth, factor_base, debug=debug)
    else:
        relations = base.filter_and_find_exponents(probable_smooth, factor_base)

    if timing: perf_time_array.append(("4", time.perf_counter()))
    if debug > 0:
        print(f"Number of relations (fully factored over the factor base): {len(relations)}")
        if debug > 1:
            print("\nRelations with full factorization over the factor base:")
            for x, exponents in relations:
                print(f"x={x}, exponents={exponents}")
        print("\nBuilding A and finding basis vectors...")
        if timing: perf_time_array.append(("debug", time.perf_counter()))

    ### 5 ###
    A = np.array([exponents for _, exponents in relations], dtype=int)
    A = (A % 2).astype(bool)
    nullspace_basis_vectors = find_left_nullspace_basis_vectors(A)

    if timing: perf_time_array.append(("5", time.perf_counter()))
    if debug > 0:
        print(f"Shape of exponent matrix A: {A.shape}")
        if debug > 1:
            print("\nExponent matrix A (mod 2):")
            print(A.astype(int))
        print("Left nullspace basis vectors:")
        print(f"- Number of basis vectors: {len(nullspace_basis_vectors)}")
        print(f"- Shape of basis vectors: {nullspace_basis_vectors[0].shape if nullspace_basis_vectors else 'N/A'}")
        if debug > 1:
            for vec in nullspace_basis_vectors:
                print(vec)
        print("\nTrying basis vectors to find a nontrivial factor...")
        if timing: perf_time_array.append(("debug", time.perf_counter()))
    
    ### 6. ###
    factor = base.test_found_subsets(N, factor_base, relations, nullspace_basis_vectors)

    ### Return or Retry ###
    
    if timing: perf_time_array.append(("6", time.perf_counter()))

    if factor != -1:
        if debug: print(f"Found a nontrivial factor: {factor}\n")
        return factor
    else:
        if debug: print(f"Tried all {len(nullspace_basis_vectors)} basis vectors, but found no nontrivial factor.\n")

        if retries <= 0:
            raise ValueError("Failed to find a nontrivial factor, try increasing B.")
        else:
            if debug: print(f"\n\nRetrying with increased B (attempts left: {retries})...\n")
            return quadratic_sieve(
                N,
                B=int(B*retry_factor),
                chunks=chunks,
                jobs=jobs,
                retries=retries-1,
                retry_factor=retry_factor,
                multivariant=multivariant,
                one_large_prime=one_large_prime,
                debug=debug,
                timing=timing
                )