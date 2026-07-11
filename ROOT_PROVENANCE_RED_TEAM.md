# Root-provenance red-team finding

## Implementation correction

Square-base experiments now represent each coordinate by an immutable
`RootedBase(N, root=b_i, base=a_i)` satisfying

\[
a_i=b_i^2\pmod N.
\]

An ordered `RootedBaseFamily` carries those pairs from selection through
relation testing and factor extraction.  The factor API accepts that family,
not independent `roots` and `bases` lists.  It first checks

\[
z\in L=\{z\in\mathbb Z^d:\prod_i a_i^{z_i}=1\pmod N\},
\]

then evaluates the product of the specifically stored roots.  It never finds
or substitutes a modular square root of an `a_i`.

Raw random residues remain explicitly sampling-only: because they were not
constructed as retained squares, they have no square-root factor endpoint.

## Reassessment of the N = 437 example

For both root families below, the squared circuit bases are
`(4, 9, 85)`, and `z=(1,1,1)` belongs to `L`.

| retained roots | stored-root product | classification | extraction |
|---|---:|---|---|
| `(2, 3, 73)` | `1` | `L0` | no factor |
| `(2, 3, 326)` | `208` | `L minus L0` | `gcd(207,437)=23` (also `gcd(209,437)=19`) |

There is no failure once the roots actually selected for the circuit are
retained.  The first selection correctly yields no factor from this relation;
the second correctly yields a factor.  Equal squared residues imply that a
residue-only sample distribution cannot distinguish these *two different root
selections*, but post-processing is not required to infer the roots from the
distribution: it already knows which roots it selected.

Accordingly, this example supports an **implementation metadata requirement**,
not a standalone “root-provenance obstruction” claim.  Any stronger novelty
claim based on the example should be removed.

## Regression coverage

The focused tests verify that malformed `(root, base)` pairs are rejected,
factor classification cannot be called with an unpaired roots list, vectors
outside `L` never reach the GCD endpoint, selector outputs preserve every
root/base pair, and both retained-root outcomes above are classified exactly.
