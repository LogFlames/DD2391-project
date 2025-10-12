def quadratic_sieve(N):
    """
    Quadratic Sieve algorithm (simplified pseudocode)
    Input:  N (composite integer)
    Output: a nontrivial factor of N
    """

    # -------------------------------
    # 1. Choose a smoothness bound B
    # -------------------------------
    B = choose_smoothness_bound(N)
    # B controls the size of the factor base; a typical choice is
    # exp(0.5 * sqrt(log(N) * log(log(N))))

    # ----------------------------------------
    # 2. Build the factor base of small primes
    # ----------------------------------------
    factor_base = []
    for p in primes_up_to(B):
        if legendre_symbol(N, p) == 1:  # N is a quadratic residue mod p
            factor_base.append(p)

    # --------------------------------------
    # 3. Search for "B-smooth" Q(x) = x² - N
    # --------------------------------------
    relations = []
    x_start = ceil(sqrt(N))
    x = x_start

    while len(relations) <= len(factor_base):
        Qx = x * x - N
        factors = trial_division(Qx, factor_base)

        if factors_are_only_from_base(factors, factor_base):
            # store both x and its factorization
            relations.append((x, factors))
        x += 1

    # ------------------------------------------------
    # 4. Build exponent matrix (parity vectors mod 2)
    # ------------------------------------------------
    # Each row corresponds to one relation (x, Q(x))
    # Each column corresponds to one prime in the factor base
    matrix = []
    for (x, factors) in relations:
        row = []
        for p in factor_base:
            e = exponent_of(p, factors)
            row.append(e % 2)  # even→0, odd→1
        matrix.append(row)

    # -----------------------------------------------
    # 5. Find a linear dependency (mod 2)
    # -----------------------------------------------
    # Gaussian elimination mod 2 gives a subset of rows (indices)
    # whose XOR (sum mod 2) is all zeros.
    subset_indices = find_linear_dependency_mod2(matrix)

    # -----------------------------------------------
    # 6. Combine those relations into X² ≡ Y² (mod N)
    # -----------------------------------------------
    X = 1
    Y_squared = 1
    for i in subset_indices:
        x_i, factors_i = relations[i]
        X = (X * x_i) % N
        Y_squared *= product_of_primes(factors_i)  # multiply Q(x)
    Y = integer_sqrt(Y_squared)

    # -----------------------------------------------
    # 7. Compute gcd to extract a factor
    # -----------------------------------------------
    g = gcd(X - Y, N)
    if 1 < g < N:
        return g  # found a nontrivial factor
    else:
        # try a different dependency or increase B
        return quadratic_sieve(N)
