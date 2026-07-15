# Build Regev's Circuit With Your Hands

This folder is a standalone, presentation-ready teaching demo for the research
repository one directory above it. It turns the audited Regev-style factoring
pipeline into a circuit-building activity: assemble two exponent registers,
Hadamards, reversible modular arithmetic, two inverse QFTs, and measurements,
then watch a fixed sample trace move through lattice reduction and stored-root
factor extraction.

The webcam is optional. With permission, the browser uses MediaPipe to turn an
open hand into a cursor and a thumb–index pinch into grab/release; mouse, touch,
and click-then-place controls remain available at all times. This is a browser
visualization of the repository's implemented circuit and classical endpoint,
not a quantum-computer emulator and not a live hardware run.

## Start the demo in about 60 seconds

From the repository root, run:

```bash
python3 regev_hand_circuit_demo/serve_demo.py --open
```

If the browser does not open automatically, visit:

```text
http://127.0.0.1:8000/regev_hand_circuit_demo/
```

Then:

1. Select **Start hand tracking** and allow camera access, or begin immediately
   with a mouse or touchscreen.
2. Keep **Guided build** on for a first presentation.
3. Pinch a component, move it over the glowing slot, and open your fingers to
   release it. With a mouse, drag and drop it or click the piece and then its
   slot.
4. Use the QFT buttons to compare the exact transform with one or two omitted
   phase layers.
5. Place both measurement blocks and select **Run lattice recovery**.

For a guaranteed hands-off backup, use **Presentation autoplay**. Fullscreen,
reset, mouse, and touch controls do not require the camera or MediaPipe network
download.

> Camera access normally works on `localhost`/`127.0.0.1` because browsers treat
> those origins as secure contexts. Opening `index.html` directly with a
> `file://` URL can prevent camera access and can also block loading the JSON
> data, so use the included server.

## What a visitor is building

The demonstration uses this concrete toy instance:

| Quantity | Demo value | Meaning |
|---|---:|---|
| Integer to factor | $N=55$ | The final factors are $5$ and $11$. |
| Stored roots | $b_1=2,b_2=3$ | These exact roots must be retained for factor extraction. |
| Circuit bases | $a_1=4,a_2=9$ | The modular-arithmetic bases, with $a_i=b_i^2\pmod {55}$. |
| Dimensions | $d=2$ | Two exponent registers and two Fourier coordinates. |
| Fourier modulus | $M=32$ | Each exponent register represents $0,\ldots,31$. |
| Exponent qubits | $5+5$ | Five qubits per exponent register because $\log_2 32=5$. |
| Result qubits | $6$ | Enough to encode residues modulo 55. |
| Auxiliary qubits | $7$ | Clean workspace for reversible modular arithmetic. |
| Total logical qubits | $23$ | $5+5+6+7$; this excludes classical bits. |
| Samples per attempt | $m=7$ | Seven two-coordinate Fourier measurements feed recovery. |

The circuit computes the modular-product label

$$
h_A(x_1,x_2)=4^{x_1}9^{x_2}\pmod {55}.
$$

Hadamards create the notebook's finite uniform box over the exponent values.
The reversible arithmetic writes the modular product into the shared result
register while preserving both exponent registers. A separate inverse QFT is
then applied to each exponent register, and measuring those registers produces
one pair $(w_1,w_2)$. The quantum stage produces structured samples—not the
factors themselves.

The browser's required build order follows the implementation:

```text
x1 and x2 exponent registers
        -> Hadamard preparation
        -> result and auxiliary registers
        -> modular exponentiation by 4^x1 and 9^x2
        -> one inverse QFT per exponent register
        -> one measurement per exponent register
        -> augmented lattice, LLL, relation verification, factor extraction
```

Hovering, selecting, or placing a piece updates the explanation panel with its
plain-language definition, mathematical role, and the corresponding source
symbol. **Guided build** unlocks pieces in the verified sequence. **Circuit
challenge** exposes every piece and explains an incorrect placement instead of
only showing a red error.

## What the completion animation does—and does not prove

The factor animation is a **fixed successful replay** chosen so that a live
presentation reaches the full classical endpoint reliably. It is model A, the
notebook's uniform hard-box state, at $N=55$, $M=32$, cutoff $t=3$ (one
omitted qubit-separation layer), and seed
`2026091301`. Its seven displayed samples are:

```text
(6, 19), (3, 10), (16, 16), (6, 19), (0, 0), (16, 16), (10, 29)
```

The exact augmented-lattice/LLL decoder recovers the relation

$$
z=(3,-1).
$$

It is verified without using the known factors:

$$
4^3 9^{-1}\equiv 1\pmod {55},
$$

so $z$ belongs to the circuit-base relation lattice $L$. Classification uses
the permanently stored generating roots, not arbitrary modular square roots:

$$
\beta=2^3 3^{-1}\equiv21\pmod {55},\qquad \beta^2\equiv1\pmod {55}.
$$

Because $\beta\not\equiv\pm1\pmod {55}$, the relation is outside the useless
subgroup $L_0$. The ordinary greatest-common-divisor step then gives

$$
\gcd(21-1,55)=5,\qquad \gcd(21+1,55)=11.
$$

This replay is an explanatory trace, not a new experimental endpoint, an
estimate of success probability, or—by itself—evidence that cutoff $t=3$ is
reliable for hard-box sampling. It was selected because it succeeds; the
separate frozen aggregate supplies the empirical evidence about the cutoff.
The known factors are shown only after the factor-blind relation checks and gcd
extraction.

## The QFT research question represented by the controls

The repository asked whether the earlier requirement to retain the exact QFT
showed a real loss of factoring information or conservatism in a worst-case
certificate. Under the frozen values $d=2$, $m=7$, and allowed loss
$\Delta=0.05$, the original product-QFT certificate certified **zero omitted
layers**. That means the sufficient bound required exact QFT; it did not prove
that every approximate QFT must fail.

The later held-out study froze eight semiprimes
`55, 65, 85, 95, 115, 119, 133, 161`, three values
$M\in\{8,16,32\}$, the hard-box and finite discrete-Gaussian state models, and
64 coupled replicates per cell. It treated $N$, rather than repeated shot
batches, as the unit of generalization. At the preregistered absolute `0.10`
non-inferiority margin:

- Omitting one QFT phase layer met the frozen rule in all six
  model-by-$M$ cells.
- Omitting two layers met the rule only for the finite-Gaussian model at
  $M=16$ and $M=32$. At the tighter post-hoc `0.05` margin, the two-layer
  result remained at Gaussian $M=32$ but not at $M=16$.
- More aggressive truncations often failed, so the result is not a universal
  safety claim.

For this $d=2$, $M=32$ circuit, the controls report exact QFT-only resource
differences:

| Setting | Logical controlled phases removed | Transpiled QFT-only CX removed | QFT-only depth removed |
|---|---:|---:|---:|
| Exact | 0 | 0 | 0 |
| Omit one layer | 2 | 4 | 0 |
| Omit two layers | 6 | 12 | 0 |

The largest observed saving in this setting is therefore six logical
controlled-phase gates and 12 QFT-only CX gates. It is **not a demonstrated end-to-end hardware speedup**: modular arithmetic can dominate the full
circuit, and the fixed transpilation showed no QFT-only depth reduction at
$M=32$. The empirical conclusion is also limited to small semiprimes, $d=2$,
$M\le32$, $m=7$, two finite exact state models, and this repository's LLL
decoder. It does not establish safe truncation for cryptographic-scale Regev
factoring, arbitrary states, hardware noise, or every post-processor.

Why this matters: rejecting a cutoff with an all-input worst-case bound is not
the same as observing information loss on the prepared modular-fiber state.
The held-out result motivates sharper, state- and recovery-aware QFT precision
certificates while keeping the stronger general claim open.

For the complete derivation, protocol, tables, and limitations, see the root
[README](../README.md), [certificate-gap report](../QFT_CERTIFICATE_GAP_REPORT.md),
and [frozen protocol](../QFT_CERTIFICATE_GAP_PROTOCOL.md).

## Hand, mouse, and touch controls

### Hand tracking

- Hold one hand where the camera can see the full palm.
- Move the hand to move the on-screen cursor. The video is mirrored so the
  interaction feels natural.
- Bring thumb and index fingertips together and hold briefly to grab.
- Keep the pinch closed while moving; open it over a highlighted target to
  release.
- The circular cursor indicator shows pinch progress. Smoothing, hysteresis,
  enlarged hit areas, and generous snapping make placement less fragile.

The implementation uses MediaPipe's browser Hand Landmarker. It tracks 21 hand
landmarks and derives a scale-normalized pinch from landmark 4 (thumb tip) and
landmark 8 (index tip). Inference is attempted with GPU delegation and falls
back to CPU. MediaPipe's synchronous video inference can occupy the browser's
main thread; this small demo skips duplicate video frames, but moving inference
to a Web Worker would be the appropriate production optimization.

### Accessible fallback

- Drag pieces with a mouse, pen, or touch.
- Or click/tap a piece and then click/tap its intended slot.
- Keyboard focus, live status text, and ordinary buttons remain usable without
  the webcam.
- The interface respects the browser's reduced-motion preference.

## Camera privacy and network behavior

Camera frames stay in the browser tab; this application has no upload endpoint
and does not record frames. The first hand-tracking start downloads the pinned
MediaPipe JavaScript/WASM package and hand-landmarker model from Google's/CDN
hosting, so hand controls need network access unless those files have already
been cached. The rest of the demo, including mouse/touch building and autoplay,
is local.

Stop the local server with `Ctrl+C`. Closing the tab or stopping hand tracking
releases the camera stream.

## Troubleshooting

| Symptom | What to do |
|---|---|
| Camera permission never appears | Use the included `http://127.0.0.1:8000/...` URL, not `file://`, and check the browser's site permissions. |
| Hand model cannot load | Check the network, then use mouse/touch or autoplay; all educational content remains available. |
| Pinch is jumpy | Improve front lighting, keep the whole palm visible, and move slightly farther from the camera. |
| Pieces do not drop | Release over the glowing slot. Mouse users can click a piece and then the slot. |
| Another process uses port 8000 | Run `python3 regev_hand_circuit_demo/serve_demo.py --port 8080`. |
| The presentation machine has no Python | Serve the repository root with any static HTTP server and open `/regev_hand_circuit_demo/`. |

For a live talk, load the page once while online, grant camera permission, test
fullscreen, and keep autoplay as the fallback. A short spoken walkthrough is
in [PRESENTATION_SCRIPT.md](PRESENTATION_SCRIPT.md).

## Folder map

| File | Purpose |
|---|---|
| `index.html` | Semantic three-panel presentation layout and circuit slots. |
| `styles.css` | Responsive visual design, animations, mirrored camera, and reduced-motion behavior. |
| `app.js` | Circuit state, guided/challenge logic, pointer interactions, QFT evidence, sample/lattice animation, and autoplay. |
| `hand-tracking.js` | Camera lifecycle, pinned MediaPipe setup, landmark drawing, smoothing, and pinch detection. |
| `demo-data.json` | Audited component explanations, parameters, resource counts, claims, and the fixed completion replay. |
| `serve_demo.py` | Zero-dependency local static server rooted at the repository. |
| `test_demo.py` | Standard-library consistency and claim-scope checks. |
| `PRESENTATION_SCRIPT.md` | A concise live-demo narration and recovery plan. |

Run the folder checks from the repository root:

```bash
python3 -m unittest regev_hand_circuit_demo/test_demo.py -v
```

If `pytest` is installed, this works too:

```bash
python3 -m pytest regev_hand_circuit_demo/test_demo.py -q
```

## Primary references

- Oded Regev, [*An Efficient Quantum Factoring Algorithm*](https://arxiv.org/abs/2308.06572).
- A. K. Lenstra, H. W. Lenstra Jr., and L. Lovász,
  [*Factoring Polynomials with Rational Coefficients*](https://doi.org/10.1007/BF01457454)
  (the original LLL algorithm).
- Google AI Edge,
  [*Hand landmarks detection guide for Web*](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker/web_js).
- Qiskit API documentation,
  [*QFTGate*](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.circuit.library.QFTGate).
