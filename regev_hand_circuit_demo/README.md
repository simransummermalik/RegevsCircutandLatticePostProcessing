# Build the Circuit

This is an intentionally plain presentation demo. The browser shows a camera,
the empty circuit, and one block at a time. Pinch or drag each block into the
outlined slot. There is no dashboard, explanation panel, QFT menu, sample
display, or lattice animation.

After all 12 blocks are placed, the page shows `55 = 5 × 11`. That final screen
is a fixed teaching endpoint—not the result of a new factoring run in the
browser.

## Start the demo

Open Terminal and run:

```bash
cd /Users/summermalik/Desktop/regevs
python3 regev_hand_circuit_demo/serve_demo.py --open
```

If the page does not open automatically, visit:

```text
http://127.0.0.1:8000/regev_hand_circuit_demo/
```

Keep Terminal open during the demo. Press `Ctrl+C` when you are finished.

## Use it

1. Select **Start camera** and allow camera access.
2. Put one open hand in view.
3. Pinch the block shown at the bottom of the page.
4. Move it to the outlined circuit slot and open your hand.
5. Repeat until the circuit is complete.

You can also drag blocks with a mouse or tap the current block and then its
outlined slot. **Reset** starts the build again.

## What is being assembled

The teaching instance uses:

| Quantity | Value |
|---|---:|
| Integer | $N=55$ |
| Stored roots | $b_1=2$, $b_2=3$ |
| Circuit bases | $a_1=4$, $a_2=9\pmod {55}$ |
| Fourier dimensions | $d=2$ |
| Fourier modulus | $M=32$ |
| Exponent-register size | 5 qubits each |
| Result-register size | 6 qubits |
| Auxiliary workspace | 7 qubits |
| Total logical qubits | 23 |

The 12 blocks are two exponent registers, two Hadamard preparations, a result
register, an auxiliary register, two modular-exponentiation operations, two
inverse QFTs, and two measurements. The modular arithmetic represents

$$
4^{x_1}9^{x_2}\pmod {55}.
$$

In the implemented research pipeline, the quantum circuit produces structured
samples. Classical lattice post-processing—not the circuit by itself—must
recover and verify a useful relation before extracting factors.

## Exact scope and limitations

- This page is an interaction layer, not a quantum simulator or quantum
  hardware interface.
- Placing a block changes only the visualization. It does not execute that
  quantum operation.
- Completing the build does not calculate the factors. The page always reveals
  the fixed successful teaching endpoint `55 = 5 × 11`.
- The simplified screen deliberately does not display samples, construct an
  augmented lattice, run LLL, classify a relation with the stored roots, or
  perform a live gcd calculation.
- The circuit drawing is schematic. It shows the main registers and operations,
  not a gate-level decomposition or hardware routing.
- The inverse-QFT blocks do not provide a precision selector. Removing the old
  QFT dashboard from this presentation does not strengthen or change the
  repository's QFT research claims.
- The fixed successful replay recorded in the research data uses the notebook's
  uniform hard-box model, $N=55$, $M=32$, seven samples, one omitted separation
  layer, and seed `2026091301`. It is not a new experimental endpoint, and a
  selected successful replay is not a recovery probability estimate.
- The held-out QFT evidence is limited to eight small semiprimes, $d=2$,
  $M\le32$, $m=7$, two finite exact state models, and this repository's LLL
  decoder. It does not establish safe truncation at cryptographic scale, under
  arbitrary noise, or for every decoder.
- At $d=2,M=32$, omitting one separation layer removed two logical controlled
  phases and four transpiled QFT-only CX gates, but did not reduce QFT-only
  depth. This is not a universal safety claim and not a demonstrated end-to-end
  hardware speedup.

For technical provenance, the recorded successful replay recovered
$z=(3,-1)$ and verified $4^3 9^{-1}\equiv1\pmod {55}$. Retaining the roots that
generated those circuit bases gives
$\beta=2^3 3^{-1}\equiv21\pmod {55}$; the subsequent gcd step yields 5 and 11.
Those calculations belong to the research pipeline. The minimal presentation
page neither runs nor animates them.

The full evidence and claim boundaries remain in the repository's root
[README](../README.md),
[certificate-gap report](../QFT_CERTIFICATE_GAP_REPORT.md), and
[frozen protocol](../QFT_CERTIFICATE_GAP_PROTOCOL.md).

## Camera notes

The video is mirrored so movement feels natural. Hand tracking uses the thumb
tip and index-finger tip to recognize a pinch. Camera frames stay in the
browser; this demo has no upload or recording endpoint.

Starting the camera downloads the pinned MediaPipe hand model. If it cannot
load, use the mouse. For the best tracking, use front lighting and keep your
whole hand visible.

Do not open `index.html` directly. Use the local address above so the browser
can load the demo data and request camera permission. If port 8000 is busy,
run:

```bash
python3 regev_hand_circuit_demo/serve_demo.py --open --port 8080
```

## Files

| File | Purpose |
|---|---|
| `index.html` | Minimal camera, circuit slots, block dock, and completion dialog |
| `minimal.css` | Presentation layout and visual styling |
| `app.js` | One-block-at-a-time placement and reset behavior |
| `hand-tracking.js` | Camera, MediaPipe landmarks, and pinch detection |
| `demo-data.json` | Audited circuit parameters and component order |
| `serve_demo.py` | Local web server |
| `test_demo.py` | Static consistency and claim-scope tests |
| `PRESENTATION_SCRIPT.md` | Short narration for the minimal page |
