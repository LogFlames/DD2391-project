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

The QS looks for numbers $x,y$ such that $$x\not\equiv\pm y \pmod{n}\quad\land\quad x^2\equiv y^2\pmod{n}.$$

This is because, such numbers $x,y$ untrivially fulfill $$(x-y)(x+y)\equiv 0\pmod{n},$$ suggesting that $(x\pm y)$ might contain divisors of $n$, which is tested with $\gcd{(x-y,n)}$.

*Note: $\gcd$ is implemented with Euclidian Division.*

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

To efficiently find perfect squares $x_f^2,y_f^2$ that fulfill $x_f^2\equiv y_f²\pmod{n}$, the QS utilizes a trick by defining $$Q(x)=(x+\lfloor\sqrt{n}\rfloor)^2-n=\tilde{x}^2-n,$$

noting that $$Q(x)\equiv \tilde{x}^2\pmod{n}\quad\forall x.$$

We then compute $\mathbb{Q}=\{Q(x_i),\cdots\}$ for many $x_i$, and find subsets $\mathbb{Q}^*\subset\mathbb{Q}$ such that $$\prod_{Q(x_j)\in\mathbb{Q}^*}{Q(x_j)}=y_f^2$$
is a perfect square. Now, since $Q(x)\equiv\tilde{x}^2\pmod{n}$, $$\left(\prod_{Q(x_j)\in\mathbb{Q}^*}{Q(x_j)}\right)\equiv\tilde{x}_{j_1}^2\tilde{x}_{j_2}^2\cdots\pmod{n}$$
$$=(\tilde{x}_{j_1}\tilde{x}_{j_2})^2\pmod{n}=x_f^2\pmod{n}$$
and thus $x_f²=y_f^2\pmod{n}$, which is the pair we were looking for! Now, how do we find appropriate $x_i$?

### Sieve setup

Our $x_i$ should allow us to efficiently find whether the product $y_f^2$ of $\mathbb{Q}^*=\{Q(x_j)\cdots\}$ is a perfect square. This is true if the sum of the exponents of the prime factors of $Q(x_j)\in\mathbb{Q}^*$ are all even. Since we need to find all these factors, we will want all $Q(x_j)$ to be small, and for them to be factored over a fixed set of small prime numbers, **the factor base**.

We ensure $Q(x)$ are small by bounding $x$ to lie inside the **sieving interval**, $x\in[-M,M]$.

If $x$ lies in the sieving interval, and if some prime $p$ divides $Q(x)$, we note that $$\tilde{x}^2\equiv n\pmod{p},$$

which is known as $n$ being a **quadratic residue mod $p$**. The Legendre Symbol $$\left(\frac{n}{p}\right)=\begin{cases}1\,&\text{if $n$ is a quadratic residue mod $p$}\\0\,&\text{if $p|n$}\\-1\,&\text{otherwise}\end{cases}$$ encodes whether $n$ is a quadratic residue mod $p$ for **any** $\tilde{x}$. For primes for which $n$ is not a quadratic residue mod $p$, we know that $Q(x)$ will never be divisible by $p$ for any $x$, and therefore useless for our algorithm. The Legendre Symbol is used by the QS to filter out such primes.

Lastly, we limit the size of the primes to be less than some bound $B$, which depends on $n$ (more on that later). $Q(x)$ will be said to be **$B$-smooth** if all of its prime factors are $\leq B$.

*Note: negative numbers are included by including $-1$ in the factor base.*

*Note: some authors let $Q(x)=x^2-n$ and set a different sieving interval.*

### Sieving

With the factor base determined, we sieve through the sieving interval $x$, calculate $Q(x)$, and check if $Q(x)$ factors completely over our factor base. If it does, it is said to have **smoothness** *(be $B$-smooth)*. If it does not, we throw it out.


<!---
TODO: Optimizations (3.2)

It is very inefficient to test each $Q(x)$ for divisibility by each prime $p$ one at a time. Instead, we will sieve the entire interval at once by noting that if $p|Q(x)$, then $p|Q(x+p)$. Equivalently, 
--->

### Building the matrix

Let $B$ be the number of primes in the factor base, and $R$ the number of discovered $B$-smooth $Q(x)$.

If $Q(x)$ is $B$-smooth, then we put the exponents (mod 2) of the primes in the factor base into a vector. These vectors are put into the matrix $A$ of size $R\times B$, where row $i$ represents the exponents mod 2 of $Q(x_i)$. We are looking for a subset of rows such that the sum of each exponent is congruent to 0 (mod 2), i.e. $\mathbb{Q}^*$.

We can represent this problem as determining bits $e_i\in\{0,1\}$ such that
$$\sum_{i=0}^k\vec{a_i}e_i=\vec{0}\pmod{2},$$
where $k$ is the number of prime factors, and $\vec{a_i}$ a row in $A$. Equivalently: $$\vec{e}A=\vec{0}\pmod{2},$$
where $\vec{e}=(e_1,e_2,\dots,e_k)$.

### Finding $\mathbb{Q}^*$ and factor testing

Gaussian elimination lets us find the spanning set of the solution space of this problem. Each element of the spanning set corresponds to a subset $\mathbb{Q}^*$ whose product is a perfect square.

So, finally, we test whether the subsets yield a factor of $n$ with GCD. For RSA, our use-case, we know that the two factors are prime. When we find a factor of $n$, we are done! For non-RSA factoring, primality and further factoring is in order.

*Note: for Gaussian elimination to work, we need $R>B$.*

*Note: there may be several subsets $\mathbb{Q}^*$, and hopefully there are, since some may not give factors of $n$.*

*Note: since at least half of the relations from the solution space will give a proper factor, if the factor base has $B$ elements and we have $R=B+k$ values $Q(x)$, then the probability of finding a proper factor is $$1-1/2^k,$$ or, for instance, $1023/1024\approx 0.999$ if $k=10$.*

## QS optimizations

### Sieving optimizations

### Parallelization

## Author's notes

Author: Eskil Nyberg

Based on Eric Landquist's write-up on the Quadratic Sieve.

Please note that the Quadratic Sieve isn't actually feasible for real-world FREAK exploitation, since it is too inefficient for the factoring of 512-bit RSA keys. However, it is a good factorization algorithm that serves as a proof-of-concept of how factorization works.