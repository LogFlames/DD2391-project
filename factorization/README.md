### Factorization for FREAK

# The Quadratic Sieve as a toy example to understand sieving

## Requirements

Install the requirements with
```bash
cd ./factorization
python3 -m pip install -r src/requirements.txt
```

The requirements for standard use of this library are:
```python
numpy           # necessary for QS
sympy           # necessary for QS
pycryptodome    # for random prime generation
cryptography    # for RSA modulus handling
tqdm            # for progress bars
```

The standard implementation of the QS requires only `numpy`, `sympy` and `tqdm`. A variant without `tqdm` is available. `pycryptodome` and `cryptography` are used by wrapper files.

---

There are also variants of the QS that use `numba` and `sage.all`. Install `numba` with 
```bash
cd ./factorization
python3 -m pip install -r requirements2.txt
# or equivalently
python3 -m pip install numba
```

## Running the Quadratic Sieve

## Implementation details

## Folder structure