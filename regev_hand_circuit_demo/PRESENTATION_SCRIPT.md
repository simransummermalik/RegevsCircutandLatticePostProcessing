# Presentation script: Build Regev's Circuit With Your Hands

This is a roughly four-minute walkthrough. The sentences in quotation marks
can be read nearly verbatim; the stage directions are optional.

## Before the audience arrives

1. From the repository root, run:

   ```bash
   python3 regev_hand_circuit_demo/serve_demo.py --open
   ```

2. Grant camera access, confirm that an open hand moves the cursor, and test a
   pinch. Keep the full palm in frame with even front lighting.
3. Press **Reset**, return to **Guided build**, select **Exact QFT**, and enter
   fullscreen.
4. Keep a mouse nearby. If the camera or network fails, use mouse/touch or
   press **Presentation autoplay**; the scientific content is identical.

## 0:00–0:35 — Set up the problem

> “This is a small but complete teaching instance of Regev-style factoring.
> We are factoring 55, but the point is to expose the architecture: a quantum
> circuit creates structured Fourier samples, and a classical integer-lattice
> decoder has to turn those samples into a factor-yielding relation. The
> circuit never simply prints 5 and 11.”

Gesture to the three panels.

> “The left side contains the verified pieces. The center is the live circuit,
> and the right side explains what each piece is, why the algorithm needs it,
> and where it exists in the repository.”

## 0:35–1:35 — Build the quantum sampler

Pinch and place the two exponent registers and their Hadamards. If gesture
tracking is not cooperating, switch to the mouse without apologizing for it.

> “There are two five-qubit exponent registers, so this is a two-dimensional
> Fourier experiment with values from zero to 31 in each direction. The
> notebook prepares a uniform hard-box state with Hadamards. Regev's full
> formulation uses a discrete-Gaussian state, and the repository keeps those
> models separate.”

Place the result and auxiliary registers, then both modular-exponentiation
blocks.

> “The selected roots are 2 and 3, but the circuit bases are their squares, 4
> and 9 modulo 55. Reversible arithmetic computes 4 to the x-one times 9 to the
> x-two modulo 55. The six result qubits hold that residue, and seven auxiliary
> qubits provide clean reversible workspace. Altogether this demo circuit uses
> 23 logical qubits.”

## 1:35–2:25 — Explain the QFT finding carefully

Before placing the QFT blocks, switch between **Exact**, **Omit 1 layer**, and
**Omit 2 layers** so the audience can see phase connections disappear and the
evidence card update. Return to **Omit 1 layer** for the supported headline.

> “Our research question was whether an earlier exact-QFT requirement revealed
> real information loss or only a conservative proof bound. Under the frozen
> five-percent certificate budget, the worst-case theorem approved no omitted
> layers. Importantly, certificate rejection is not a proof of algorithmic
> failure.”

> “Across eight held-out semiprimes, omitting one layer met the preregistered
> non-inferiority rule in all six hard-box and finite-Gaussian settings. Here at
> M equals 32 that removes two logical controlled phases and four QFT-only CX
> gates. Two layers removes six controlled phases and 12 QFT-only CX gates, but
> that stronger cutoff passed only for the finite-Gaussian model at M equals 16
> and 32—not for this hard-box model as an aggregate.”

> “There was no QFT-only depth saving at M equals 32, and we did not demonstrate
> an end-to-end hardware speedup. This is a finite, decoder-specific
> certification gap, not a universal claim that approximate QFT is safe.”

Place both QFTs and both measurements.

## 2:25–3:30 — Follow samples to factors

When the completion dialog appears, select **Run lattice recovery**.

> “For presentation reliability, this animation uses one fixed successful
> hard-box replay: N equals 55, M equals 32, cutoff t equals three—one omitted
> phase-separation layer—and seed 2026091301. It was selected because it reaches
> the endpoint, so the replay itself is an explanation, not a success-rate
> estimate. The separate frozen aggregate supplies the cutoff evidence.”

Point to the seven sample cards as they enter the pipeline.

> “The decoder clears denominators, builds an exact augmented integer lattice,
> runs LLL, and recovers z equals three, minus one. Shortness is not enough: the
> code verifies that 4 cubed times 9 inverse is one modulo 55.”

Point to the stored-root classification.

> “Now root provenance matters. Using the stored roots 2 and 3 gives beta equal
> to 2 cubed times 3 inverse, which is 21 modulo 55. Beta squared is one, but
> beta is neither plus one nor minus one. That places the relation outside the
> useless L-zero class. GCD of 20 with 55 gives 5, and GCD of 22 with 55 gives
> 11.”

## 3:30–4:00 — Close on the contribution

> “The point is not that a browser animation factored a hard number. The point
> is that the demo connects every layer we audited: state preparation,
> reversible modular arithmetic, multidimensional Fourier sampling, exact
> lattice construction, relation verification, stored-root classification,
> and factor extraction.”

> “The defensible finding is narrower: in this frozen small-scale regime, a
> worst-case QFT certificate was more conservative than the held-out recovery
> endpoint. That tells us where a sharper, state-aware precision theorem could
> save gates without confusing certificate failure with information loss.”

## Short answers for likely questions

**Is this running on a quantum computer?**  
No. It is an interactive visualization of the audited circuit and a fixed
classically reproduced recovery trace. The repository contains exact finite
sampling models and circuit construction, but this page is not a hardware run.

**Why use squared bases?**  
The circuit relations are defined by $a_i=b_i^2\bmod N$. A useful relation
makes the stored-root product a nontrivial square root of one, which the final
gcd step can split.

**Why must the roots be stored?**  
The same squared residue can have several modular roots. Factor extraction
must use the particular $b_i$ that generated each $a_i$; choosing a root later
would change the algorithm.

**Does one successful replay show that truncation works?**  
No. The replay is deliberately fixed for the exhibit. The evidence comes from
the frozen eight-modulus, 64-replicate-per-cell study with $N$ as the
generalization unit.

**What exactly was saved?**  
At $d=2,M=32$, one omitted layer removes two logical controlled phases and four
QFT-only transpiled CX gates. Two layers removes six and 12. QFT-only depth did
not decrease in that setting, and no full-circuit hardware speedup was claimed.

**Does this scale to RSA?**  
Not established. The result is limited to small semiprimes, $d=2$, $M\le32$,
$m=7$, two finite state models, and the current LLL decoder.

## Emergency fallback

If hand tracking fails during the talk:

1. Say, “The camera is only an input method; the circuit logic is unchanged.”
2. Use the mouse, or select **Presentation autoplay**.
3. Continue the scientific narration from the QFT evidence card.

Do not refresh repeatedly on stage: refreshing can trigger another camera
permission prompt and discard cached hand-model initialization.
