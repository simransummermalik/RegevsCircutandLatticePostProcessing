# Short presentation script

## Before the presentation

Run:

```bash
cd /Users/summermalik/Desktop/regevs
python3 regev_hand_circuit_demo/serve_demo.py --open
```

Select **Start camera**, test one placement, and then select **Reset**. Keep a
mouse nearby as a fallback.

## While building

Say:

> “This is a simple visual model of a Regev-style sampling circuit for the
> teaching integer 55. I will assemble it one block at a time.”

Place the two exponent-register and Hadamard blocks.

> “The circuit has two exponent registers. The Hadamards prepare the uniform
> state used by the original notebook.”

Place the result, auxiliary, and modular-exponentiation blocks.

> “The roots are 2 and 3, and the bases used by the circuit are their squares:
> 4 and 9 modulo 55. The arithmetic computes 4 to the first exponent times 9
> to the second exponent, modulo 55.”

Place the two inverse-QFT and measurement blocks.

> “The inverse Fourier transforms and measurements produce structured samples.
> The quantum circuit does not directly output the factors; a complete research
> run also needs verified classical lattice post-processing.”

## When the result appears

Say:

> “The page now shows 55 equals 5 times 11. This is a fixed teaching endpoint,
> not a live quantum run and not a new success-rate measurement. The demo is
> only making the circuit architecture easy to see and build.”

That is the end of the demo. The page intentionally has no second dashboard,
QFT control screen, sample animation, or recovery overlay.

## If the camera fails

Say:

> “The camera is only an input method.”

Then drag the same block with the mouse. The circuit order and fixed completion
screen are unchanged.
