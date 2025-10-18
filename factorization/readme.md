## NOTE TO EXAMINERS:

||
|:-:|
|**This file contains supplementary information to understand intrinsics about the Quadratic Sieve and our implementation of it. Additionally, [math.md](math.md) contains details on the mathematics behind the sieve. ALL important details from this repository have been added to the broad [README.md](../README.md) in the root directory.**|
|**Disregard this file!**|


### Factorization for FREAK

# The Quadratic Sieve (QS) as a toy example to understand integer factorization

The Quadratic Sieve is the fastest algorithm known to find large factors for numbers with about 30~100 digits, but not for numbers larger than that. 512-bit RSA moduli are 154 digits long, and this algorithm is NOT fast enough for the factorization of such numbers in a reasonable amount of time.

However, the Quadratic Sieve serves as a good example algorithm to understand how the real algorithms used for such factorization work, namely the General Number Field Sieve (GNFS) or the Special Number Field Sieve.

Note! The Quadratic Sieve excels at finding  arbitrary **large** factors. There are many other efficient algorithms to quickly find factors that are small or on a special form which should be used before this algorithm, since they are better.

## Directory structure

* **[README.md](README.md) - this file**
* **[math.md](math.md) - detailed math write-up**
* **[run.py](run.py) - interface for the Quadratic Sieve**
* **[requirements.txt](requirements.txt) - Python module requirements for the sieve**
* **[src/](src/) - Python source code**
  * **[quadratic_sieve.py](quadratic_sieve.py) - Interfacing logic**
  * **[break_rsa.py](break_rsa.py) - Interfacing logic for RSA key files**
  * **[qslib/](qslib/) - Quadratic Sieve source code**
    * **[base.py](base.py) - Simple source code**
    * **[parallel_np_sieving.py](src/qslib/parallel_np_sieving.py) - Parallelization logic**
    * **[one_large_prime.py](src/qslib/one_large_prime.py) - OLP variant**
    * **[complete.py](complete.py) - Production code**
    * ...

## Requirements

Install the requirements with
```bash
$ cd ./factorization
$ python3 -m pip install -r src/requirements.txt
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

There is also a variant of the QS that uses SageMath, an external library to quickly perform the linear algebra. Since it is convoluted to install, it is not used per default.

## Running the Quadratic Sieve
You can interact with the Quadratic Sieve via `run.py`:
```bash
$ cd ./factorization
$ python3 run.py -h
$ python3 -m run -h # also works
$ ./run.py -h # also works, Linux only
```

Via `run.py` you can directly run factorizations with the `factor` mode. The `complete` module is used per default. For example:

```bash
# 100-bit / 30-digit composite of two large primes
$ N="730263881119727212489103570233"

# factorization of number with default options:
$ python3 run.py factor -N "$N"

# single-core factorization:
$ python3 run.py factor -N "$N" -J 1

# generate and factorize a 100-bit number, retry up to 2 times, with retry factor 1.2, and print time taken
$ python3 run.py factor --bits 100 -R 2 -RF 1.2 -t
```

You can also interact with the sieve in a Python REPL with either of the below options:
```bash
# via run.py, does not support command history
$ python3 run.py repl
# via Python, supports command history
$ python3 -i src/quadratic_sieve.py

# default debug and timing options can be set
$ python3 run.py repl -v -t
$ python3 -i src/quadratic_sieve.py -v -t
```

### Advanced usage

There are many additional command line options. See them all with `python3 run.py -h`. Here are some examples:

```bash
# list available variants / modules (for use with -M)
$ python3 run.py list_variants

# generate and factorize a 60-bit number using the "base" module
$ python3 run.py factor -M base --bits 60

# generate and factorize a 100-bit number, retry up to 2 times, with retry factor 1.2, using the "One Large Prime" option, while printing timing and debug information
$ python3 run.py factor --bits 100 -R 2 -J 8 -OLP -t -v
```

Here is the `-h` output:

```
usage: run.py [-h] [-M {base,np,parallel,complete,olp,sagemath}] [-b BITS] [-n NUMBER] [-B B_PARAMETER] [-C CHUNKS] [-J JOBS] [-R RETRIES] [-RF RETRY_FACTOR] [-PV {multiprocessing,multithreading}] [-OLP] [-v] [-vv] [-t] {factor,list_variants,gen_composite,repl}

positional arguments:
  {factor,list_variants,gen_composite,repl}
    Mode to run: 'factor' to factor a number, 'list_variants' to list available variants, 'gen_composite' to generate a composite number N = p*q, or 'repl' to start a Python REPL. Most optional arguments only apply to the 'factor' mode.

options:
  -h, --help
    show this help message and exit
  -M, --module {base,np,parallel,complete,olp,sagemath}
    Module (Quadratic Sieve variant) to use.
  -b, --bits BITS
    Number of bits of the composite number to generate and factor (incompatible with --number).
  -n, -N, --number NUMBER
    Composite number to factor (overrides --bits).
  -B, --B-parameter B_PARAMETER
    Manually set the B-smoothness bound.
  -C, --chunks CHUNKS
    (Only compatible with some variants.) Number of chunks to split work into, for parallel variants. Can be larger than -J.
  -J, --jobs JOBS
    (Only compatible with some variants.) Number of jobs to run in parallel, for parallel variants.
  -R, --retries RETRIES
    (Only compatible with some variants.) Number of retries on failure.
  -RF, --retry-factor RETRY_FACTOR
    (Only compatible with some variants.) Factor to increase the smoothness bound B by on each retry.
  -PV, --parallelization-variant {multiprocessing,multithreading}
    (Only compatible with some variants.) Parallelization variant to use. Recommended: multiprocessing.
  -OLP, --one-large-prime
    (Only compatible with some variants.) Use the 'one-large-prime' variant for the 'complete' module.
  -v, --verbose
    (Only compatible with some variants.) Default debug level to 1.
  -vv, --very-verbose
    (Only compatible with some variants.) Default debug level to 2.
  -t, --timing
    (Only compatible with some variants.) Enable timing by default.
```

### Super advanced usage

It is possible to use `multithreading` instead of `multiprocessing`, however Python's global interpreter lock (GIL) will cause this parallelization method to grant virtually no speed-up. It is possible to install a Python with this disabled, called "free-threaded Python", however this still does not lead to a speed-up when compared to the multiprocessing implementation. The only real use-case is to implement a more current process bar than the one across chunks, or another form of inter-thread communication.

The below installation commands work only for Linux and require `pyenv` to be installed.

```bash
$ pyenv install python-3.14t-dev
$ ~/.pyenv/versions/3.14t-dev/bin/python3.14t -m venv ~/.venv_3.14t
$ source ~/.venv_3.14t/bin/activate
$ python3 -m pip install factorization/requirements.txt
```
Running with GIL disabled:
```bash
$ PYTHON_GIL=0 python3 run.py factor -PV multithreading [args...]
```

## How does the Quadratic Sieve work?

How nice of you to ask! The basic premise is that we are looking for numbers

$$x\not\equiv\pm y \pmod{n}\quad\land\quad x^2\equiv y^2\pmod{n}.$$

This is because, such numbers $x,y$ untrivially fulfill $$(x-y)(x+y)\equiv 0\pmod{n},$$ suggesting that $(x\pm y)$ might contain divisors of $n$, which is tested with $\gcd{(x-y,n)}$.

We find such numbers by doing logarithmic sieving (a bit like the Sieve of Eratosthenes does it) to find numbers that have a certain factor composition, and then use these numbers to construct numbers which fulfill the relation above.

### See [math.md](math.md)...
... for all the nitty gritty details about this, how we find such numbers $x,y$, and everything else about the math that goes into the Quadratic Sieve (or at least, everything we understand). Head over there for mathematical details!

## What's missing for GNFS/SNFS?

The GNFS, the variant that works for all numbers, works similarly to the QS but with some major distinctions:

* Both the GNFS/SNFS and the QS look for numbers on the form $x^2=y^2\pmod{N}$.
* GNFS works with two Number Fields, which are extensions of the rational numbers defined by a polynomial. The fields are connected via a homomorphism.
* The factor base is instead elements of these fields.
* Sieving is done to check a bunch of polynomials for certain attributes (rather than the $Q(x)=(x+\sqrt{N})^2-N$ that the QS uses), eventually finding polynomials which fulfill a property related to B-smoothness.
* With enough relations the GNFS eventually finds squares in both number fields, which are mapped to $x^2=y^2\pmod{N}$ that we can check, in contrast to products of $Q(x)$.
* Because the Number Field Sieves contains a lot of number theory - complex numbers, polynomials, etc. - the math and algorithm used becomes really complex really quickly.

We believe the QS serves as an illustrative example for how the process of using the broad idea behind the production-ready GNFS / SNFS works, and how we can optimize and parallelize sieving, without doing unfathomable amounts of math.

The SNFS is slightly faster, but can only factor numbers on the form $r^e \pm s$.

## Implementation details

* src/qslib/
  * [base.py](src/qslib/base.py) --- Implements a basic Quadratic Sieve with few optimizations and no parallelization. It is good example code to follow to understand the implementation.
  * [np_sieving.py](src/qslib/np_sieving.py) --- Implements improvements via numpy for the sieving, providing an about 15x speedup (no asymptotic improvement).
  * [parallel_np_sieving.py](src/qslib/parallel_np_sieving.py) --- Implements parallelization (via `multiprocessing` by default). Don't use `multithreading` unless you know what you're doing (it's slower).
  * [one_large_prime.py](src/qslib/one_large_prime.py) --- Implements the "one large prime" variant of the sieve, which doesn't filter out numbers with large primes in the hope of them helping to find enough relations in the end.
  * [complete.py](src/qslib/complete.py) --- The production ready variant complete with debug, timing information, retries, progress bars via tqdm, and some other quality of life features. This is the default variant used!
  * [sagemath_linalg.py](src/qslib/sagemath_linalg.py) --- Uses the SageMath library for faster linear algebra. Due to the complexity of installing SageMath and making it available to Python, this is not the default. Note: SageMath cannot be installed via pip!

## Tried, and failed, optimizations

Note: the sieving and linear algebra are the only parts of the algorithm that are relevant to optimize. Our linear algebra is okay, and we've elected to focus our optimizations efforts on the sieving part:

Tried sieving optimizations:

* Using gmpy2 bigintegers for operations in Python. Didn't help.
* Using numpy arrays for efficient storage of integers (as dtype=object). Didn't help.
* Using numba's jit/njit compilations. Didn't help or couldn't handle large numbers.
* Sieving in C (via LLM translation from Python). Due to complexity of transferring bigints (GMP) from C to Python, this does not seem possible / fast.