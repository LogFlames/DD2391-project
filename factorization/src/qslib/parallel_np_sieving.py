"""Written with LLM assistance."""

from typing import Literal

###################################
# Improvement for step 3: Sieving #
# ------ Parallelizing operations #
###################################

import math
from sympy import sqrt_mod
import numpy as np

def parallel_sieving(N, factor_base, M,
        num_jobs=1,
        max_parallel_jobs=1,
        variant: Literal["multiprocessing", "multithreading"]="multiprocessing"
        ):
    """
    Perform the sieving step of the Quadratic Sieve algorithm in parallel.

    Will only parallelize if num_jobs > 1 and max_parallel_jobs > 1.
    
    :param N: The integer to be factored.
    :param factor_base: List of primes in the factor base.
    :param M: The sieving interval parameter.
    :param num_jobs: Number of jobs to split the sieving into.
    :param max_parallel_jobs: Maximum number of parallel jobs to run concurrently.
    :param variant: "multiprocessing" or "multithreading" to choose parallelization method.
    WARNING: Multithreading is GIL-bound and will not yield speedup. Even with GIL disabled on a freethreaded version of Python, speed-up is not achieved (except maybe for quite small numbers).
    :param __sieve_worker: INTERNAL, used for custom sieve worker function.
    :return: List of tuples (x, Q(x)) where Q(x) is B-smooth.
    """
    factor_base = np.array(factor_base) # ensure numpy array for efficiency

    if num_jobs < 1:
        raise ValueError("num_jobs must be at least 1")
    elif num_jobs > 1:
        probable_smooth = _parallel_sieving(N, factor_base, M, num_jobs, max_parallel_jobs, variant)
    else:   # single-core sieving
        factor_base_roots = [
            np.array(sqrt_mod(N, p, all_roots=True), dtype=object)
            if sqrt_mod(N, p, all_roots=True)
            else np.array([], dtype=object) for p in factor_base
            ]
        
        probable_smooth = _sieve_worker(N, math.isqrt(N), factor_base, factor_base_roots, M, -M, M+1)
        probable_smooth = list(map(tuple, probable_smooth))
    return probable_smooth

def _parallel_sieving(N, factor_base, M, num_jobs, num_parallel_jobs, variant):
    """Function to control parallel sieving across threads / processes."""
    probable_smooth = set()
    sqrt_N = math.isqrt(N)

    # Precompute roots for each prime
    factor_base_roots = [
        np.array(sqrt_mod(N, p, all_roots=True), dtype=object)
        if sqrt_mod(N, p, all_roots=True)
        else np.array([], dtype=object) for p in factor_base
        ]

    # Compute only chunk bounds, pass chunk generation to _sieve_worker
    interval_min, interval_max = -M, M+1
    interval_len = interval_max - interval_min

    chunk_size = interval_len // num_jobs
    bounds = [
        (i*chunk_size, (i+1)*chunk_size if i != num_jobs-1 else interval_len)
        for i in range(num_jobs)
    ]

    inputs = [
        (N, sqrt_N, factor_base, factor_base_roots, M, interval_min + start, interval_min + end)
        for start, end in bounds
    ]
    
    if variant == "multiprocessing":
        import multiprocessing.pool

        with multiprocessing.pool.Pool(processes=num_parallel_jobs) as pool:
            results = list(pool.imap(sieve_worker_controller, inputs))
    elif variant == "multithreading":
        import concurrent.futures as futures

        with futures.ThreadPoolExecutor(max_workers=num_parallel_jobs) as executor:
            results = list(executor.map(sieve_worker_controller, inputs))
    else: raise ValueError("variant must be 'multiprocessing' or 'multithreading'")
    
    for res in results:
        probable_smooth.update(res)
    
    probable_smooth = list(probable_smooth)
    return probable_smooth

def sieve_worker_controller(args):
    """Multi-processing compatible helper."""
    return _sieve_worker(*args)

def _sieve_worker(N, sqrt_N, factor_base, factor_base_roots, M, start, end):
    """
    Sieving loop, can be run in parallel with custom (start, end) parameters.
    
    Please see base sieving function for comments.
    """
    # function is not faster with gmpy2 integers
    # function is not faster with numpy arrays for bigints
    # function is not compatible with numba njit / jit

    interval = range(start, end)
    probable_smooth = set()
    
    sieve_array = [math.log(abs((sqrt_N + x)**2 - N)) for x in interval]
    sieve_array = np.array(sieve_array)

    for j in range(len(factor_base)):
        p = factor_base[j]
        roots = factor_base_roots[j]

        for r in roots:
            power = p

            while power <= 2*M:
                offset = ((sqrt_N + interval[0]) - r) % power
                if offset != 0:
                    offset = power - offset
                for j in range(offset, len(interval), power):
                    sieve_array[j] -= np.log(p)
                power *= p

        for j in np.where(sieve_array < 0.5)[0]:
            x = sqrt_N + interval[j]
            y = pow(x, 2) - N
            probable_smooth.add((x, y))

    return probable_smooth

################################
# QS with parallelized sieving #
################################

import src.qslib.base as base
from typing import Literal

def quadratic_sieve(N: int, B: int|Literal["auto"]="auto", num_jobs: int=1, max_parallel_jobs: int=1, variant: Literal["multiprocessing", "multithreading"]="multiprocessing") -> int:
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
    probable_smooth = parallel_sieving(N, factor_base, M, num_jobs, max_parallel_jobs, variant)
    relations = base.filter_and_find_exponents(probable_smooth, factor_base)
    nullspace_basis_vectors = base.find_sets_of_squares(relations)
    factor = base.test_found_subsets(N, factor_base, relations, nullspace_basis_vectors)

    if factor != -1:
        # Successful factorization
        return factor
    else:
        raise ValueError("Failed to find a nontrivial factor of N, try increasing B.")