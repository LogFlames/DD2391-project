"""
Implementation of the "One Large Prime" variant of the Quadratic Sieve algorithm.

This variant allows relations that are almost B-smooth, containing exactly one prime
larger than the factor base (and smaller than some "large prime bound").
These are called partial relations and later on we pair two such relations that share
the same large prime. That way we produce more full relations.
"""

from sympy import isprime

def one_large_prime(B, probable_smooth, factor_base):
    """
    Implements the 1-large-prime variant of the Quadratic Sieve algorithm.

    Given probable smooth (x, y) pairs, returns:
     - one list of (x, [exponents]) where exponents[i] = exponent of factor_base[i]
       in the factorization of y = x^2 - N.
     - another list of (x, [exponents], value) where value is the large prime
       number p fow which is true B < p < prime_bound

    It uses trial division - only for the probable smooth numbers we found before.
    IT returns relations that are completely factored over the factor base and in addition,
    it also records partial relations that contain exactly one prime larger than the 
    factor base (but below "prime_bound").
    """
    prime_bound = 10*B
    full_relations = []
    partial_relations = []

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
                full_relations.append((x, exponents))
                break
            elif (value < prime_bound) and isprime(value):
                # append x, its prime factors's exponents and the remainder
                partial_relations.append((x, exponents, value))

    return full_relations, partial_relations

def combine_relations(partial_relations, N):
    """
    Combines partial relations (into pairs) that share the same large prime number
    and turns them into full relations.
    
    Two partial relations with the same large prime can be multiplied together to
    "cancel" that prime (the exponent becomes even), producing a full B-smooth relation.
    """
    full_relations = []
    combinations ={}    # partials by prime

    for x1, exponents1, prime in partial_relations:
        if prime in combinations:
            x2, exponents2, prime = combinations.pop(prime)
            x = (x1 * x2) % N
            exponents = [(e1 + e2) for e1, e2 in zip(exponents1, exponents2)]
            full_relations.append((x, exponents))
        else:
            combinations[prime] = (x1, exponents1, prime)

    return full_relations