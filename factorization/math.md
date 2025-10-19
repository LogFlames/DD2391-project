### Factorization for FREAK

# Understanding the Quadratic Sieve (QS)

Project Group 18 for **DD2391 Cybersecurity Overview** at KTH Royal Institute of Technology. *October 2025.*

#### Note: this document is mostly paraphrased from Eric Landquist's write-up on the Quadratic Sieve, with some clarifications and (in our opinion) more transparent terminology.

## References

Landquist, Eric. *The Quadratic Sieve Factoring Algorithm*. (Dec 14, 2001). MATH 448: Cryptographic Algorithms at The University of Nebraska-Lincoln.
https://www.math.unl.edu/~mbrittenham2/classwk/445f08/dropbox/landquist.quadratic.sieve.pdf

## QS basics

### Mathematical aim

$n$ is the number to be factored. 

The QS looks for numbers $x,y$ such that 

$$x\not\equiv\pm y \pmod{n}\quad\land\quad x^2\equiv y^2\pmod{n}.$$

This is because, such numbers $x,y$ untrivially fulfill

$$(x-y)(x+y)\equiv 0\pmod{n},$$

suggesting that $(x\pm y)$ might contain divisors of $n$, which is tested with $\gcd{(x-y,n)}$.

*Note: $\gcd{}$ is implemented with Euclidian Division.*

> #### **Factor example**
> 
> For instance, if $$(x-y)(x+y)=kn=kpq$$ where $pq=n$ are the prime divisors of $n$, then we have that
> 
> $$x^2\equiv y^2\pmod{p}\implies x\equiv\pm y\pmod{p},$$
> $$x^2\equiv y^2\pmod{q}\implies x\equiv\pm y\pmod{q}.$$
> 
> If the signs are of the same parity ($+$ and $+$, or $-$ and $-$) then both $p$ and $q$ divide $x-y$ or $x+y$, that is, $n$ divides one of the factors: $x\equiv\pm y\pmod{n}$, which contradicts that $x\not\equiv\pm y\pmod{n}$. In this case, no factor is discovered.
> 
> If the signs are of different parity, then the factorization is successful:
> 
> $$\gcd{(x-y,n)=p},$$
> $$\gcd{(x+y,n)=q},$$
>
> i.e. $p,q$ are spread out across the two factors.
> 
> *Note 2: Landquist remarks that there is at least a $1/2$ chance that the factor, $x-y$, will be untrivial. This, we believe, refers to the separation of factors.*

### Discovering $x,y$

To efficiently find perfect squares $x_f^2,y_f^2$ that fulfill $x_f^2\equiv y_f²\pmod{n}$, the QS utilizes a trick by defining

$$Q(x)=(x+\lfloor\sqrt{n}\rfloor)^2-n=\tilde{x}^2-n,$$

noting that

$$Q(x)\equiv \tilde{x}^2\pmod{n}\quad\forall x.$$

We then compute $\mathbb{Q}=\{Q(x_i),\cdots\}$ for many $x_i$, and find subsets $\mathbb{Q}^*\subset\mathbb{Q}$ such that

$$\prod_{Q(x_j)\in\mathbb{Q}^*}{Q(x_j)}=y_f^2$$

is a perfect square. Now, since $Q(x)\equiv\tilde{x}^2\pmod{n}$,

$$\left(\prod_{Q(x_j)\in\mathbb{Q}^*}{Q(x_j)}\right)\equiv\tilde{x}_{j_1}^2\tilde{x}_{j_2}^2\cdots\pmod{n}$$

$$=(\tilde{x}_{j_1}\tilde{x}_{j_2})^2\pmod{n}=x_f^2\pmod{n}$$

and thus $x_f²=y_f^2\pmod{n}$, which is the pair we were looking for! Now, how do we find appropriate $x_i$?

### Sieve setup

Our $x_i$ should allow us to efficiently find whether the product $y_f^2$ of $\mathbb{Q}^*=\{Q(x_j)\cdots\}$ is a perfect square. This is true if the sum of the exponents of the prime factors of $Q(x_j)\in\mathbb{Q}^*$ are all even. Since we need to find all these factors, we will want all $Q(x_j)$ to be small, and for them to be factored over a fixed set of small prime numbers, **the factor base**.

The factor base consists of every prime number up until some bound $B$ we have previously chosen.  $Q(x)$ will be said to be **$B$-smooth** if it can be factored completely over prime numbers from the factor base and only factors from the factor base. That is, if all of its prime factors are $\leq B$.

We ensure $Q(x)$ are small by bounding $x$ to lie inside the **sieving interval**, $x\in[-M,M]$.

If $x$ lies in the sieving interval, and if some prime $p$ divides $Q(x)$, we note that

$$\tilde{x}^2\equiv n\pmod{p},$$

which is known as $n$ being a **quadratic residue mod $p$**. The Legendre Symbol 

$$\left(\frac{n}{p}\right)=\begin{cases}1\,&\text{if $n$ is a quadratic residue mod $p$}\\0\,&\text{if $p|n$}\\-1\,&\text{otherwise}\end{cases}$$

encodes whether $n$ is a quadratic residue mod $p$ for **any** $\tilde{x}$. For primes for which $n$ is not a quadratic residue mod $p$, we know that $Q(x)$ will never be divisible by $p$ for any $x$, and therefore useless for our algorithm. QS uses Euler’s criterion as a way to compute the Legendre symbol and filter out such primes.

Euler’s Criterion states that for an odd prime $p$ and an integer $a$ not divisible by $p$,

$$\left( \frac{a}{p} \right) \equiv a^{\frac{p-1}{2}} \pmod{p}.$$

In other words,

$$ a^{\frac{p-1}{2}} \equiv \begin{cases} 1 & \text{if } a \text{ is a quadratic residue mod } p, \\ -1 & \text{if } a \text{ is a nonresidue mod } p. \end{cases} $$

*Note: negative numbers are included by including $-1$ in the factor base.*

*Note: some authors let $Q(x)=x^2-n$ and set a different sieving interval.*

*Note: Bound $B$ depends on $n$ (more on that later).*

### Sieving

With the factor base determined, we sieve through the sieving interval $x$, calculate $Q(x)$, and check if $Q(x)$ factors completely over our factor base. If it does, it is said to have **smoothness**  *(be $B$-smooth)*. If it does not, we throw it out - since we only want $B$-smooth numbers.

Instead of testing every $Q(x)$ one by one (which is slow), we use a sieving trick to quickly find all $Q(x)$ that are likely smooth.

First, we find where each prime number $p$ from the factor base divides $Q(x)$.
For every prime $p$ in the factor base, we find all $x$ such that:

$$x^2 ≡ n \pmod{p}$$

These are the **roots** $\pmod{p}$.  
For each root $r$, every $x ≡ r \pmod{p}$ will make $p | (x^2 − n)$. So, $p$ divides $Q(x)$ for a whole arithmetic sequence of $x$’s:

$$x = r, r + p, r + 2p, ...$$

If $Q(x)$ is the product of some primes from the factor base, then the logarithm of $Q(x)$ is the sum of the logarithms of these primes:

$$ Q(x) = p_1 * p_2 * p_3 * ... \Rightarrow \ln(Q(x)) = \ln(p_1) + \ln(p_2) + \ln(p_3) + ... $$

With that in mind, we calculate $\ln(Q(x))$ for every $Q(x)$. Each time a prime $p$ divides one of those $Q(x)$, we subtract $\ln(p)$ from the corresponding $\ln(Q(x))$ - if $p^k$ $Q(x)$, we subtract $k * \ln(Q(x))$. If $Q(x)$ factors completely over the factor base, the value of $\ln(Q(x))$ will be theoretically reduced to $0$.
After we process all the primes from the factor base, the $Q(x)$'s whose corresponding $\ln(Q(x))$ values have been reduced to $0$ (or close to $0$) are the ones that are smooth - or almost smooth. These values are the ones we are interested in.

After we find our pairs of $(x, Q(x))$ where $Q(x)$ is a probable $B$-smooth number, we use trial division to find exactly which prime numbers $p$ from the factor base divide $Q(x)$ and put each prime's exponent in its corresponding place in a vector.

> For example, if the factor base contains 10 prime numbers $p_1, p_2, ..., p_{10}$ and $Q(x_i) = p_2 * p_6 * p_7^2 * p_9$ for some $x_i$, then $x_i$'s vector will be:
> 
> $$[0, 1, 0, 0, 0, 1, 2, 0, 1, 0]$$

### Building the matrix

Let $B$ be the number of primes in the factor base, and $R$ the number of discovered $B$-smooth $Q(x)$.

If $Q(x)$ is $B$-smooth, then we put the exponents (mod 2) of the primes in the factor base into a vector. These vectors are put into the matrix $A$ of size $R\times B$, where row $i$ represents the exponents mod 2 of $Q(x_i)$. We are looking for a subset of rows such that the sum of each exponent is congruent to 0 (mod 2), i.e. $\mathbb{Q}^*$.

We can represent this problem as determining bits $e_i\in\{0,1\}$ such that
$$\sum_{i=0}^k\vec{a_i}e_i=\vec{0}\pmod{2},$$

where $k$ is the number of prime factors, and $\vec{a_i}$ a row in $A$. Equivalently:

$$\vec{e}A=\vec{0}\pmod{2},$$

where $\vec{e}=(e_1,e_2,\dots,e_k)$.

### Finding $\mathbb{Q}^*$ and factor testing

Gaussian elimination lets us find the spanning set of the solution space of this problem. Each element of the spanning set corresponds to a subset $\mathbb{Q}^*$ whose product is a perfect square.

So, finally, we test whether the subsets yield a factor of $n$ with GCD. For RSA, our use-case, we know that the two factors are prime. When we find a factor of $n$, we are done! For non-RSA factoring, primality and further factoring is in order.

*Note: for Gaussian elimination to work, we need $R>B$.*

*Note: there may be several subsets $\mathbb{Q}^*$, and hopefully there are, since some may not give factors of $n$.*

*Note: since at least half of the relations from the solution space will give a proper factor, if the factor base has $B$ elements and we have $R=B+k$ values $Q(x)$, then the probability of finding a proper factor is*

$$1-1/2^k,$$

*or, for instance, $1023/1024\approx 0.999$ if $k=10$.*

## QS optimizations

### Parallelization

We can easily parallelize the computations by dividing the sieving interval into smaller pieces and sieving in several parts, using several processes, possible on several computers. This also keeps the temporary data manageable.

### One-Large-Prime

The One-Large-Prime (1LP) variant is an optimization of the basic Quadratic Sieve (QS) algorithm that increases the number of relations without greatly increasing the computation time needed.

In the basic QS algorithm, a value $Q(x) = x^2 - N$ is only accepted if it is completely $B$-smooth, meaning that it factors completely over the factor base (and only the factor base). However, in practice, there are a lot of values $Q(x)$ that are "_almost_ smooth" - they factor completely over the factor base except for one additional prime number $p$ that is larger than the bound $B$. These are called "partial relations".

The basic QS algorithm "discards" these partial relations. However, the 1LP variant takes advantage of them. Essentially, the 1LP variant accepts values $Q(x)$ that contain exactly one prime factor greater than $B$ and stores them temporarily. Then, it combines one partial relation with another that shares the same large prime. When two such relations are multiplied together, they produce a "_full_ relation" that can be used in the exponent matrix in the next step of the algorithm.

When we multiply the two $Q(x)$ values:

$$ Q(x_1) * Q(x_2) = (x^1_2−N)(x^2_2−N) $$

each has a factor of the same large prime $p$. That way, the exponent of $p$ becomes an even number (more specifically $2$) and therefore cancels out, as we use modulo $2$ in the exponent vector. This way, the product of $Q(x_1)$ and $Q(x_2)$ becomes $B$-smooth.

In short, two partial relations with the same large prime can be combined into one full relation.

### Multiple-Polynomial Quadratic Sieve

There is also the **Multi-Polynomial Quadratic Sieve (QLP)** which replaces $Q(x)=(x+sqrt(N))^2-N$ with several polynomials on the form $(ax+b)^2-N$, where $a,b$ are chosen to keep the numbers smaller. This variant is not implemented by us.

### Additional optimizations

* Obviously, not writing it in Python. Also using faster libraries for arithmetic such as C:s GMP.
* The linear algebra can be optimized for sparse matrices (which is the case, especially for larger inputs). See Block Lanczos. A part of its computation can be parallelized, but not the entire computation.

## Author's notes

Authors: Eskil Nyberg, Venetia Ioanna Papadopoulou

Based on Eric Landquist's write-up on the Quadratic Sieve.

Please note that the Quadratic Sieve isn't actually feasible for real-world FREAK exploitation, since it is too inefficient for the factoring of 512-bit RSA keys. However, it is a good factorization algorithm that serves as a proof-of-concept of how factorization works.