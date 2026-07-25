"""Build three poster-readable plots from frozen experiment outputs.

These plots complement the native
``results/qft_certificate_gap/certification_vs_recovery.png`` figure:

1. QFT-only CX savings for the largest empirically passing Regev cutoff.
2. Worst-instance Shor recovery change under selected strong QFT errors.
3. The finite RV-structured comparator versus ordinary bounded recovery.

No result is recomputed here. The script only aggregates frozen CSV/JSON
outputs and checks the expected row counts before plotting.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results graphs"

NAVY = "#13294B"
ORANGE = "#FF5F05"
BLUE = "#1F77B4"
PURPLE = "#7E57C2"
GREEN = "#2A9D6F"
GRAY = "#737B86"
LIGHT_GRAY = "#E8EBEF"
RED = "#C43C39"


def _finish(fig: plt.Figure, filename: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        OUT / filename,
        dpi=240,
        facecolor="white",
        bbox_inches="tight",
    )
    plt.close(fig)


def build_regev_resource_plot() -> None:
    gap = pd.read_csv(
        ROOT / "results/qft_certificate_gap/certificate_gap_rows.csv"
    )
    configurations = pd.read_csv(
        ROOT / "results/qft_certificate_gap/configuration_rows.csv"
    )

    model_labels = {
        "A_uniform_hard_box": "Uniform",
        "B_exact_finite_discrete_gaussian": "Gaussian",
    }
    rows: list[dict[str, object]] = []
    for selected in gap.itertuples(index=False):
        matches = configurations[
            (configurations["M"] == selected.M)
            & (configurations["model"] == selected.model)
            & (
                configurations["omitted_layers"]
                == selected.empirically_noninferior_layers
            )
        ]
        resource_columns = [
            "compiled_cx",
            "compiled_cx_saving",
            "cp_saving",
            "compiled_depth_saving",
        ]
        unique = matches[resource_columns].drop_duplicates()
        if len(unique) != 1:
            raise AssertionError(
                f"expected one resource tuple for M={selected.M}, "
                f"model={selected.model}; found {len(unique)}"
            )
        resource = unique.iloc[0]
        rows.append(
            {
                "label": f"M={selected.M} · {model_labels[selected.model]}",
                "model": str(selected.model),
                "exact_cx": int(
                    resource["compiled_cx"] + resource["compiled_cx_saving"]
                ),
                "selected_cx": int(resource["compiled_cx"]),
                "cx_saving": int(resource["compiled_cx_saving"]),
                "cp_saving": int(resource["cp_saving"]),
            }
        )

    if len(rows) != 6:
        raise AssertionError(f"expected six frozen Regev cells; found {len(rows)}")

    frame = pd.DataFrame(rows)
    y = np.arange(len(frame))[::-1]
    fig, ax = plt.subplots(figsize=(9.4, 5.7))

    for yi, row in zip(y, frame.itertuples(index=False), strict=True):
        color = BLUE if row.model.startswith("A_") else ORANGE
        ax.plot(
            [row.selected_cx, row.exact_cx],
            [yi, yi],
            color=LIGHT_GRAY,
            linewidth=7,
            solid_capstyle="round",
            zorder=1,
        )
        ax.scatter(
            row.exact_cx,
            yi,
            s=115,
            facecolor="white",
            edgecolor=GRAY,
            linewidth=2.3,
            zorder=3,
        )
        ax.scatter(
            row.selected_cx,
            yi,
            s=135,
            color=color,
            edgecolor="white",
            linewidth=1.2,
            zorder=4,
        )
        ax.text(
            (row.selected_cx + row.exact_cx) / 2,
            yi + 0.23,
            f"{row.cx_saving} fewer",
            ha="center",
            va="bottom",
            fontsize=12,
            color=NAVY,
            fontweight="bold",
        )

    ax.set_yticks(y, frame["label"])
    ax.set_xlim(10, 56)
    ax.set_xlabel("Two-qubit CX gates in the QFT", fontsize=14)
    ax.set_title(
        "Safe QFT shortcuts removed 4–12 two-qubit gates",
        loc="left",
        fontsize=19,
        color=NAVY,
        fontweight="bold",
        pad=14,
    )
    ax.grid(axis="x", color=LIGHT_GRAY, linewidth=1)
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", labelsize=12)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(GRAY)

    ax.scatter([], [], s=115, facecolor="white", edgecolor=GRAY, linewidth=2.3,
               label="Exact QFT")
    ax.scatter([], [], s=135, color=BLUE, edgecolor="white",
               label="Uniform shortcut")
    ax.scatter([], [], s=135, color=ORANGE, edgecolor="white",
               label="Gaussian shortcut")
    ax.legend(
        frameon=False,
        ncol=1,
        loc="upper right",
        fontsize=11,
    )
    fig.text(
        0.01,
        0.01,
        "Frozen eight-semiprime holdout. QFT subcircuits only; "
        "modular arithmetic and hardware routing are excluded.",
        fontsize=10.5,
        color=GRAY,
    )
    fig.subplots_adjust(left=0.20, right=0.98, top=0.84, bottom=0.17)
    _finish(fig, "regev_qft_gate_savings.png")


def build_shor_noise_plot() -> None:
    paired = pd.read_csv(
        ROOT
        / "shor_to_regev_study/moreqftnoise/shor_qft_gate_noise/"
        "paired_rows.csv"
    )
    selected_settings = {
        "cphase_gain_0p10": ("Phase-angle error (+10%)", ORANGE),
        "rz_bias_0p10": ("RZ rotation error (+0.10 rad)", PURPLE),
        "cx_depol_0p010": ("CX depolarizing surrogate (1%)", RED),
    }

    robustness = pd.read_csv(
        ROOT
        / "shor_to_regev_study/results/shor_qft_robustness/"
        "per_instance_rows.csv"
    )
    truncation = robustness[
        (robustness["readout_bitflip_probability"] == 0.01)
        & (robustness["omitted_layers"].isin([0, 3]))
    ]
    pivot = truncation.pivot(
        index=["instance_id", "shots"],
        columns="omitted_layers",
        values="order_probability",
    ).dropna()
    pivot["change"] = pivot[3] - pivot[0]
    truncation_worst = pivot.groupby("shots")["change"].min().sort_index()
    expected_truncation_shots = [4, 8, 16]
    if list(truncation_worst.index.astype(int)) != expected_truncation_shots:
        raise AssertionError("unexpected Shor truncation shot grid")

    fig, ax = plt.subplots(figsize=(9.4, 5.7))
    for setting, (label, color) in selected_settings.items():
        rows = paired[paired["noise_setting"] == setting].sort_values("shots")
        if list(rows["shots"].astype(int)) != [1, 2, 8, 16]:
            raise AssertionError(f"unexpected shot grid for {setting}")
        ax.plot(
            rows["shots"],
            100 * rows["order_min_difference"],
            marker="o",
            linewidth=2.7,
            markersize=7,
            color=color,
            label=label,
        )

    ax.plot(
        truncation_worst.index,
        100 * truncation_worst.values,
        marker="D",
        linewidth=2.5,
        markersize=6,
        linestyle="--",
        color=GREEN,
        label="Remove 3 QFT layers + 1% readout flips",
    )

    ax.axhline(0, color=NAVY, linewidth=1.4)
    ax.axhline(
        -10,
        color=GRAY,
        linewidth=1.8,
        linestyle="--",
        label="Preset recovery boundary",
    )
    ax.axvspan(7.2, 17, color=GREEN, alpha=0.07, zorder=0)
    ax.text(
        11.2,
        -6.8,
        "No observed loss\nat 8 or 16 shots",
        ha="center",
        va="center",
        color=GREEN,
        fontsize=12,
        fontweight="bold",
    )

    ax.set_xscale("log", base=2)
    ax.set_xticks([1, 2, 4, 8, 16], ["1", "2", "4", "8", "16"])
    ax.set_xlim(0.85, 18)
    ax.set_ylim(-40, 5)
    ax.set_xlabel("Circuit shots", fontsize=14)
    ax.set_ylabel(
        "Worst held-out recovery change\n(percentage points)",
        fontsize=13,
    )
    ax.set_title(
        "More shots absorbed the tested Shor QFT errors",
        loc="left",
        fontsize=19,
        color=NAVY,
        fontweight="bold",
        pad=14,
    )
    ax.grid(color=LIGHT_GRAY, linewidth=1)
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", labelsize=12)
    ax.legend(
        frameon=False,
        fontsize=10.5,
        ncol=2,
        loc="lower right",
    )
    fig.text(
        0.01,
        0.01,
        "Worst of eight frozen Shor instances. Controlled simulations, "
        "including a global CX-noise surrogate; not hardware measurements.",
        fontsize=10.5,
        color=GRAY,
    )
    fig.subplots_adjust(left=0.15, right=0.98, top=0.84, bottom=0.18)
    _finish(fig, "shor_noise_vs_shots.png")


def build_rv_comparison_plot() -> None:
    per_n = pd.read_csv(ROOT / "results/quotient_study/per_N_rows.csv")
    reference = "common_exact_norm_LLL_bounded_enumeration"
    rv_method = "RV_structured_finite_comparator"
    subset = per_n[
        (per_n["sample_count"] == 11)
        & (per_n["method"].isin([reference, rv_method]))
    ]

    model_order = [
        "A_exact_uniform_hard_box",
        "B_exact_finite_discrete_gaussian",
        "C_theorem_consistent_noisy_dual",
        "D_circuit_derived_readout_corruption_surrogate",
    ]
    model_labels = {
        "A_exact_uniform_hard_box": "Notebook hard-box",
        "B_exact_finite_discrete_gaussian": "Finite Gaussian",
        "C_theorem_consistent_noisy_dual": "Synthetic noisy-dual",
        "D_circuit_derived_readout_corruption_surrogate": "Corruption surrogate",
    }
    absolute = (
        subset.groupby(["model", "method"])["factor_success_rate"]
        .mean()
        .unstack("method")
    )
    for model in model_order:
        counts = subset[subset["model"] == model].groupby("method")["N"].nunique()
        if counts.to_dict() != {reference: 20, rv_method: 20}:
            raise AssertionError(f"unexpected held-out N counts for {model}: {counts}")

    with (ROOT / "results/quotient_study/paired_N_comparisons.json").open() as handle:
        paired_rows = json.load(handle)
    paired = pd.DataFrame(paired_rows)
    paired = paired[
        (paired["endpoint"] == "paired N-level factor-success-rate difference")
        & (paired["method"] == rv_method)
        & (paired["reference_method"] == reference)
        & (paired["sample_count"] == 11)
    ].set_index("model")
    if set(paired.index) != set(model_order):
        raise AssertionError("missing RV paired-comparison rows")

    y = np.arange(len(model_order))[::-1]
    means = np.array([100 * paired.loc[model, "mean"] for model in model_order])
    lows = np.array(
        [100 * paired.loc[model, "bootstrap_ci_low"] for model in model_order]
    )
    highs = np.array(
        [100 * paired.loc[model, "bootstrap_ci_high"] for model in model_order]
    )
    lower_error = means - lows
    upper_error = highs - means

    fig, ax = plt.subplots(figsize=(9.4, 5.7))
    ax.axvline(0, color=NAVY, linewidth=1.8)
    ax.axvspan(-25, 0, color=ORANGE, alpha=0.055, zorder=0)
    ax.errorbar(
        means,
        y,
        xerr=np.vstack([lower_error, upper_error]),
        fmt="o",
        color=ORANGE,
        ecolor=ORANGE,
        elinewidth=2.4,
        capsize=5,
        markersize=9,
        zorder=3,
    )

    for yi, model, mean in zip(y, model_order, means, strict=True):
        baseline_rate = 100 * absolute.loc[model, reference]
        rv_rate = 100 * absolute.loc[model, rv_method]
        ax.text(
            -24.5,
            yi + 0.25,
            f"{baseline_rate:.0f}% → {rv_rate:.0f}%",
            ha="left",
            va="bottom",
            fontsize=11.5,
            color=NAVY,
            fontweight="bold",
        )
        ax.text(
            mean + (0.7 if mean <= -2 else 0.5),
            yi,
            f"{mean:+.0f} pp",
            ha="left",
            va="center",
            fontsize=11,
            color=ORANGE if mean < 0 else NAVY,
            fontweight="bold",
        )

    ax.set_yticks(y, [model_labels[model] for model in model_order])
    ax.set_xlim(-25, 5)
    ax.set_ylim(-0.65, len(model_order) - 0.25)
    ax.set_xlabel(
        "RV-style filter change versus ordinary recovery (percentage points)",
        fontsize=12.5,
    )
    ax.set_title(
        "The finite RV-style filter did not improve recovery",
        loc="left",
        fontsize=19,
        color=NAVY,
        fontweight="bold",
        pad=14,
    )
    ax.text(
        -23.8,
        3.55,
        "← fewer factors recovered",
        fontsize=11,
        color=ORANGE,
        fontweight="bold",
    )
    ax.grid(axis="x", color=LIGHT_GRAY, linewidth=1)
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", labelsize=11.5)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(GRAY)
    fig.text(
        0.01,
        0.01,
        "20 held-out semiprimes; 32 replicates each; 95% whole-N intervals. "
        "The RV theorem conditions were not met, so this tests only our finite comparator.",
        fontsize=10.2,
        color=GRAY,
    )
    fig.subplots_adjust(left=0.24, right=0.98, top=0.84, bottom=0.19)
    _finish(fig, "rv_filter_comparison.png")


def main() -> None:
    build_regev_resource_plot()
    build_shor_noise_plot()
    build_rv_comparison_plot()
    print("Wrote poster result plots to", OUT)


if __name__ == "__main__":
    main()
