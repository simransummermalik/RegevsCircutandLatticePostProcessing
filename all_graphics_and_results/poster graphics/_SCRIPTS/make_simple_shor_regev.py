#!/usr/bin/env python3
"""Create one deliberately simple, general-audience Shor/Regev comparison."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "16_SIMPLE_GENERAL_AUDIENCE"
OUT.mkdir(parents=True, exist_ok=True)

NAVY = "#13294B"
BLUE = "#0072B2"
PURPLE = "#7E57C2"
ORANGE = "#FF5F05"
TEAL = "#009E73"
SLATE = "#526273"
LIGHT_BLUE = "#EAF5FB"
LIGHT_PURPLE = "#F3EDFA"
LIGHT_GREEN = "#E9F7F2"
WHITE = "#FFFFFF"


def rounded(ax, xy, width, height, face, edge, linewidth=2.5, radius=0.18):
    patch = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle=f"round,pad=0.02,rounding_size={radius}",
        facecolor=face,
        edgecolor=edge,
        linewidth=linewidth,
    )
    ax.add_patch(patch)
    return patch


def arrow(ax, start, end, color=NAVY, linewidth=3):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=18,
            linewidth=linewidth,
            color=color,
            shrinkA=2,
            shrinkB=2,
        )
    )


def fourier_wave(ax, x0, y0, color):
    x = np.linspace(x0, x0 + 1.45, 180)
    y = y0 + 0.24 * np.sin(2 * np.pi * 4 * (x - x0) / 1.45)
    ax.plot(x, y, color=color, linewidth=4, solid_capstyle="round")
    for x_peak in np.linspace(x0 + 0.12, x0 + 1.33, 5):
        ax.add_patch(Circle((x_peak, y0 - 0.45), 0.07, facecolor=color, edgecolor="none"))


def several_samples(ax, x0, y0):
    colors = [BLUE, PURPLE, ORANGE]
    for row, color in enumerate(colors):
        y = y0 + 0.34 - row * 0.34
        for col in range(4):
            x = x0 + col * 0.36 + (row % 2) * 0.12
            ax.add_patch(Circle((x, y), 0.075, facecolor=color, edgecolor="none"))
        ax.plot([x0 - 0.08, x0 + 1.35], [y, y], color=color, alpha=0.25, linewidth=2)


def fraction_icon(ax, x0, y0):
    ax.text(x0, y0 + 0.26, "k", ha="center", va="center", fontsize=24, color=BLUE, weight="bold")
    ax.plot([x0 - 0.23, x0 + 0.23], [y0, y0], color=NAVY, linewidth=3)
    ax.text(x0, y0 - 0.25, "M", ha="center", va="center", fontsize=24, color=NAVY, weight="bold")
    ax.text(x0 + 0.62, y0, "→  r", ha="center", va="center", fontsize=26, color=BLUE, weight="bold")


def period_icon(ax, x0, y0):
    """A nontechnical repeating-stripe icon for Shor's recovered period."""
    for i in range(6):
        x = x0 + i * 0.18
        ax.plot([x, x], [y0 - 0.22, y0 + 0.22], color=BLUE, linewidth=4, solid_capstyle="round")
    ax.add_patch(
        FancyArrowPatch(
            (x0, y0 - 0.36),
            (x0 + 0.90, y0 - 0.36),
            arrowstyle="<->",
            mutation_scale=12,
            linewidth=2,
            color=BLUE,
        )
    )
    ax.text(x0 + 0.45, y0 - 0.49, "period", ha="center", va="top", fontsize=10.5, color=BLUE, weight="bold")


def lattice_icon(ax, x0, y0):
    for i in range(5):
        for j in range(4):
            ax.add_patch(Circle((x0 + i * 0.28, y0 + j * 0.28), 0.045, facecolor=NAVY, edgecolor="none", alpha=0.75))
    ax.plot([x0 + 0.01, x0 + 0.84], [y0 + 0.02, y0 + 0.86], color=ORANGE, linewidth=4)
    ax.add_patch(Circle((x0 + 0.84, y0 + 0.86), 0.09, facecolor=ORANGE, edgecolor=WHITE, linewidth=2))


def build():
    # A compact figure panel, not a poster layout.
    fig, ax = plt.subplots(figsize=(15, 5.4))
    fig.patch.set_facecolor(WHITE)
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 5.4)
    ax.axis("off")

    ax.text(7.5, 5.03, "Two quantum routes to the same factors", ha="center", va="center", fontsize=27, weight="bold", color=NAVY)
    ax.text(
        7.5,
        4.67,
        "Shor recovers one period. Regev combines several Fourier clues.",
        ha="center",
        va="center",
        fontsize=15,
        color=SLATE,
    )

    # Two plain rows designed to be dropped into a larger poster.
    rounded(ax, (0.35, 2.65), 14.30, 1.65, LIGHT_BLUE, BLUE, linewidth=2.8, radius=0.20)
    rounded(ax, (0.35, 0.55), 14.30, 1.65, LIGHT_PURPLE, PURPLE, linewidth=2.8, radius=0.20)

    # Shor row.
    ax.text(1.20, 3.63, "SHOR", ha="center", va="center", fontsize=23, weight="bold", color=BLUE)
    ax.text(1.20, 3.21, "one period", ha="center", va="center", fontsize=12.5, weight="bold", color=NAVY)
    fourier_wave(ax, 2.55, 3.66, BLUE)
    ax.text(
        3.275,
        2.96,
        "one-dimensional\nFourier pattern",
        ha="center",
        va="center",
        fontsize=12.5,
        color=NAVY,
        weight="bold",
    )
    arrow(ax, (4.25, 3.48), (4.90, 3.48), BLUE, 2.8)
    period_icon(ax, 5.12, 3.59)
    ax.text(
        7.05,
        3.60,
        "decode the repeat",
        ha="left",
        va="center",
        fontsize=15,
        color=NAVY,
        weight="bold",
    )
    ax.text(7.05, 3.27, "continued fractions", ha="left", va="center", fontsize=11.5, color=SLATE)
    arrow(ax, (10.35, 3.48), (12.10, 3.48), BLUE, 2.8)
    rounded(ax, (12.34, 3.04), 1.75, 0.86, WHITE, BLUE, linewidth=2, radius=0.14)
    ax.text(13.215, 3.47, "p × q", ha="center", va="center", fontsize=22, color=BLUE, weight="bold")

    # Regev row.
    ax.text(1.20, 1.53, "REGEV", ha="center", va="center", fontsize=23, weight="bold", color=PURPLE)
    ax.text(1.20, 1.11, "many clues", ha="center", va="center", fontsize=12.5, weight="bold", color=NAVY)
    several_samples(ax, 2.58, 1.48)
    ax.text(
        3.275,
        0.86,
        "multidimensional\nFourier samples",
        ha="center",
        va="center",
        fontsize=12.5,
        color=NAVY,
        weight="bold",
    )
    arrow(ax, (4.25, 1.38), (4.90, 1.38), PURPLE, 2.8)
    lattice_icon(ax, 5.12, 0.94)
    ax.text(
        7.05,
        1.55,
        "combine the clues",
        ha="left",
        va="center",
        fontsize=15,
        color=NAVY,
        weight="bold",
    )
    ax.text(7.05, 1.21, "lattice reduction (LLL)", ha="left", va="center", fontsize=11.5, color=SLATE)
    arrow(ax, (10.85, 1.38), (12.10, 1.38), PURPLE, 2.8)
    rounded(ax, (12.34, 0.94), 1.75, 0.86, WHITE, PURPLE, linewidth=2, radius=0.14)
    ax.text(13.215, 1.37, "p × q", ha="center", va="center", fontsize=22, color=PURPLE, weight="bold")

    destination = OUT / "Shor_vs_Regev_SIMPLE_GENERAL_AUDIENCE"
    fig.savefig(destination.with_suffix(".png"), dpi=180, bbox_inches="tight", facecolor=WHITE)
    fig.savefig(OUT / "Shor_vs_Regev_SIMPLE_GENERAL_AUDIENCE_TRANSPARENT.png", dpi=180, bbox_inches="tight", transparent=True)
    fig.savefig(destination.with_suffix(".svg"), bbox_inches="tight", facecolor=WHITE)
    fig.savefig(destination.with_suffix(".pdf"), bbox_inches="tight", facecolor=WHITE)
    plt.close(fig)


if __name__ == "__main__":
    build()
