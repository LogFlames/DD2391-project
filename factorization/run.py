#!/usr/bin/env python3
"""
Entry point for the quadratic sieve factorization modules.
Run with `python run.py [args]`
i.e. `python run.py -h` for help.
"""

import sys

if __name__ == "__main__":
    if "src" in sys.path[0]:
        print("Run from dd2391-project/factorization with:\npython3 run.py -h")
        sys.exit(1)

    from src import quadratic_sieve
    quadratic_sieve.main()
