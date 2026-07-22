#!/usr/bin/env python3
"""Create three 48 x 36 inch poster layout mockups.

These are composition guides, not result figures.  Each mockup embeds small
previews of graphics that already exist in ``poster graphics`` and labels the
recommended role for that asset.  Run from the repository root with:

    MPLBACKEND=Agg .venv/bin/python \
        "poster graphics/_SCRIPTS/make_poster_layout_options.py"
"""

from __future__ import annotations

from pathlib import Path
import textwrap

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.patches import FancyBboxPatch
from matplotlib.text import Text


ROOT = Path(__file__).resolve().parents[2]
GRAPHICS = ROOT / "poster graphics"
ASSETS = GRAPHICS / "14_SUPPLEMENTAL_VETO_OPTIONS"
DECORATIVE = GRAPHICS / "12_DECORATIVE_AI_CONCEPTS"
OUTPUT = GRAPHICS / "15_POSTER_LAYOUT_OPTIONS"

NAVY = "#0F2651"
INK = "#14213D"
ORANGE = "#EC6A2D"
CYAN = "#2DACC7"
PALE_BLUE = "#EAF4F8"
PALE_ORANGE = "#FFF2E9"
MID = "#5A6678"
LIGHT = "#F7F9FC"
WHITE = "#FFFFFF"
GREEN = "#2D8C73"


def add_round_box(fig, rect, facecolor=WHITE, edgecolor="#CBD5E1", linewidth=1.8):
    """Add an axes with a rounded-border card drawn in figure coordinates."""
    ax = fig.add_axes(rect)
    ax.set_axis_off()
    card = FancyBboxPatch(
        (0, 0), 1, 1,
        boxstyle="round,pad=0.012,rounding_size=0.025",
        transform=ax.transAxes,
        facecolor=facecolor,
        edgecolor=edgecolor,
        linewidth=linewidth,
        clip_on=False,
    )
    ax.add_patch(card)
    return ax


def add_text_card(fig, rect, number, heading, body, *, accent=ORANGE, facecolor=WHITE):
    ax = add_round_box(fig, rect, facecolor=facecolor, edgecolor=accent, linewidth=2.1)
    ax.text(
        0.045, 0.86, str(number), color=WHITE, fontsize=14, fontweight="bold",
        ha="center", va="center",
        bbox=dict(boxstyle="circle,pad=0.34", facecolor=accent, edgecolor=accent),
    )
    ax.text(0.11, 0.86, heading, color=NAVY, fontsize=17, fontweight="bold", va="center")
    wrap_width = max(38, int(110 * rect[2]))
    ax.text(
        0.055, 0.68, textwrap.fill(body, wrap_width), color=INK, fontsize=11.0,
        va="top", ha="left", linespacing=1.35,
    )
    return ax


def add_asset_card(
    fig,
    rect,
    number,
    heading,
    filename,
    role,
    *,
    accent=CYAN,
    facecolor=WHITE,
):
    ax = add_round_box(fig, rect, facecolor=facecolor, edgecolor=accent, linewidth=2.0)
    ax.text(
        0.045, 0.94, str(number), color=WHITE, fontsize=13, fontweight="bold",
        ha="center", va="center",
        bbox=dict(boxstyle="circle,pad=0.32", facecolor=accent, edgecolor=accent),
    )
    heading_size = max(10.0, min(15.5, 1780 * rect[2] / max(len(heading), 14)))
    ax.text(0.10, 0.94, heading, color=NAVY, fontsize=heading_size, fontweight="bold", va="center")

    path = ASSETS / filename
    if not path.exists():
        path = DECORATIVE / filename
    preview = ax.inset_axes([0.035, 0.16, 0.93, 0.70])
    preview.set_axis_off()
    if path.exists():
        preview.imshow(mpimg.imread(path))
    else:
        preview.set_facecolor(PALE_ORANGE)
        preview.text(0.5, 0.5, f"Missing preview\n{filename}", ha="center", va="center", color=ORANGE)
    role_size = max(7.4, min(10.2, 1750 * rect[2] / max(len(role), 20)))
    ax.text(0.05, 0.075, role, color=MID, fontsize=role_size, va="center", fontstyle="italic")
    return ax


def add_header(fig, option, title, subtitle, *, hero=None):
    header = fig.add_axes([0, 0.875, 1, 0.125])
    header.set_axis_off()
    header.set_facecolor(NAVY)
    header.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="square,pad=0", facecolor=NAVY, edgecolor=NAVY))
    if hero:
        path = DECORATIVE / hero
        if path.exists():
            bg = mpimg.imread(path)
            header.imshow(bg, extent=[0, 1, 0, 1], aspect="auto", alpha=0.24)
    header.text(0.025, 0.76, f"LAYOUT MOCKUP {option} · 48 × 36 INCHES · NOT A DATA FIGURE", color="#9FE7F1", fontsize=11.5, fontweight="bold")
    header.text(0.025, 0.43, title, color=WHITE, fontsize=26, fontweight="bold", va="center")
    header.text(0.025, 0.13, subtitle, color="#D8E5EF", fontsize=12.5, va="center")


def add_footer(fig, _note):
    footer = fig.add_axes([0.018, 0.012, 0.964, 0.035])
    footer.set_axis_off()
    footer.plot([0, 1], [0.95, 0.95], color="#CBD5E1", linewidth=1.0, transform=footer.transAxes)
    footer.text(1.0, 0.38, "Asset filenames are placement references; replace mockup labels with final prose.", color=MID, fontsize=9.5, ha="right", va="center", transform=footer.transAxes)


def option_a_story_first():
    fig = plt.figure(figsize=(16, 12), facecolor=LIGHT)
    add_header(
        fig,
        "A",
        "Story-first: question → experiment → result → limitation",
        "Best for a mixed audience that needs the research arc before the detailed plots.",
        hero="D01a_dark_header_4x1_DECORATIVE_NOT_DATA.png",
    )

    add_text_card(fig, [0.025, 0.745, 0.95, 0.105], 1, "Six-sentence TL;DR", "State what was implemented, the finite-parameter QFT question, what the certificate predicted, what held-out experiments found, the QFT-only resource change, and the exact scope limit.", facecolor=PALE_ORANGE)

    add_asset_card(fig, [0.025, 0.49, 0.285, 0.23], 2, "Beginner entry point", "S12_beginner_shor_vs_regev.png", "Use first: establish the Shor/Regev distinction.")
    add_asset_card(fig, [0.025, 0.205, 0.285, 0.255], 3, "What the code does", "S10_complete_sample_to_factor_pipeline.png", "A compact map from samples to factor extraction.")

    add_asset_card(fig, [0.33, 0.45, 0.41, 0.27], 4, "Primary result", "S03_main_six_cell_certificate_gap.png", "Largest panel: the held-out certificate-versus-recovery comparison.", accent=ORANGE)
    add_asset_card(fig, [0.33, 0.205, 0.41, 0.215], 5, "Uncertainty across N", "S04_primary_cluster_forest_plot.png", "Support the result with whole-modulus uncertainty.", accent=ORANGE)

    add_asset_card(fig, [0.76, 0.535, 0.215, 0.185], 6, "Why the certificate is conservative", "S02_certificate_threshold_log_ruler.png", "Mechanism and tested parameter range.", accent=GREEN)
    add_asset_card(fig, [0.76, 0.335, 0.215, 0.175], 7, "Resource accounting", "S05_M32_qft_only_resources.png", "Label all savings as QFT-only.", accent=GREEN)
    add_asset_card(fig, [0.76, 0.205, 0.215, 0.105], 8, "Claim boundary", "S14_scope_fence.png", "Finish with what the result does and does not show.", accent=GREEN)

    add_text_card(fig, [0.025, 0.07, 0.95, 0.105], 9, "Methods strip", "Frozen held-out semiprimes, roots, sample models, seeds, non-inferiority rule, whole-N bootstrap, and exclusions. Keep this readable but visually subordinate to the result.", accent=NAVY, facecolor=PALE_BLUE)
    add_footer(fig, "Recommended when presentation time is 4–6 minutes and the audience includes non-specialists.")
    return fig


def option_b_result_first():
    fig = plt.figure(figsize=(16, 12), facecolor=LIGHT)
    add_header(
        fig,
        "B",
        "Result-first: make the held-out finding impossible to miss",
        "Best for a research poster session where readers decide in seconds whether to stop.",
        hero="D02a_light_header_4x1_DECORATIVE_NOT_DATA.png",
    )

    add_text_card(fig, [0.025, 0.735, 0.95, 0.115], 1, "One-sentence takeaway + three number tiles", "Lead with the narrow empirical result. Put the original certificate prediction beside the best held-out truncation and the QFT-only resource counts; do not state whole-algorithm speedup.", facecolor=PALE_ORANGE)

    add_asset_card(fig, [0.025, 0.48, 0.22, 0.225], 2, "Research question", "S13_qft_phase_layer_cutaway.png", "Show exactly what is being removed from the QFT.")
    add_asset_card(fig, [0.025, 0.20, 0.22, 0.25], 3, "Experimental design", "S09_eight_heldout_moduli.png", "Make N—not repeated shots—the unit of generalization.")

    add_asset_card(fig, [0.265, 0.395, 0.47, 0.31], 4, "Hero result", "S03_main_six_cell_certificate_gap.png", "Give this plot the most area on the page.", accent=ORANGE)
    add_asset_card(fig, [0.265, 0.20, 0.47, 0.165], 5, "Whole-N uncertainty", "S04_primary_cluster_forest_plot.png", "Place immediately under the hero result.", accent=ORANGE)

    add_asset_card(fig, [0.755, 0.535, 0.22, 0.17], 6, "Certificate gap", "S02_certificate_threshold_log_ruler.png", "Explain the finite-regime disagreement.", accent=GREEN)
    add_asset_card(fig, [0.755, 0.365, 0.22, 0.145], 7, "QFT-only resources", "S05_M32_qft_only_resources.png", "Separate phase-gate and QFT-only CX counts.", accent=GREEN)
    add_asset_card(fig, [0.755, 0.20, 0.22, 0.14], 8, "Scope fence", "S14_scope_fence.png", "Use explicit verified / unverified language.", accent=GREEN)

    add_text_card(fig, [0.025, 0.07, 0.465, 0.10], 9, "Method in 40 words", "Finite exact distributions, paired random draws, frozen parameters, and whole-modulus inference. Link to the notebook and full protocol with a QR code.", accent=NAVY, facecolor=PALE_BLUE)
    add_text_card(fig, [0.51, 0.07, 0.465, 0.10], 10, "Limit in 40 words", "Toy finite models are evidence about this implementation regime. They are not proof that approximate QFT is safe for asymptotic Regev factoring or on hardware.", accent=NAVY, facecolor=PALE_BLUE)
    add_footer(fig, "Recommended when the main goal is to communicate one narrow, defensible result quickly.")
    return fig


def option_c_beginner_first():
    fig = plt.figure(figsize=(16, 12), facecolor=LIGHT)
    add_header(
        fig,
        "C",
        "Beginner-first: teach the algorithm before showing the evidence",
        "Best for a class presentation or broad computer-science audience.",
        hero="D01a_dark_header_4x1_DECORATIVE_NOT_DATA.png",
    )

    add_asset_card(fig, [0.025, 0.62, 0.30, 0.22], 1, "Why Regev instead of Shor?", "S12_beginner_shor_vs_regev.png", "Start with the two factoring strategies.", accent=CYAN)
    add_asset_card(fig, [0.35, 0.62, 0.40, 0.22], 2, "Where this project intervenes", "S10_complete_sample_to_factor_pipeline.png", "Highlight the QFT sampling stage without hiding post-processing.", accent=CYAN)
    add_asset_card(fig, [0.775, 0.62, 0.20, 0.22], 3, "What one omitted layer means", "S13_qft_phase_layer_cutaway.png", "Give a visual definition before any statistics.", accent=CYAN)

    add_text_card(fig, [0.025, 0.48, 0.95, 0.11], 4, "Research question and prediction", "Ask whether the notebook needs the exact multidimensional QFT at the tested finite parameters. Then distinguish the conservative certificate prediction from the empirical held-out question.", facecolor=PALE_ORANGE)

    add_asset_card(fig, [0.025, 0.20, 0.40, 0.25], 5, "What the held-out tests found", "S03_main_six_cell_certificate_gap.png", "Primary evidence; preserve the model A / model B distinction.", accent=ORANGE)
    add_asset_card(fig, [0.45, 0.20, 0.255, 0.25], 6, "A favorable exact example", "S08_N15_identical_measurement_law.png", "Clearly label this as a counterexample, not a general guarantee.", accent=ORANGE)
    add_asset_card(fig, [0.73, 0.325, 0.245, 0.125], 7, "What was saved", "S05_M32_qft_only_resources.png", "Report only the measured QFT-subcircuit resources.", accent=GREEN)
    add_asset_card(fig, [0.73, 0.20, 0.245, 0.10], 8, "What remains unknown", "S14_scope_fence.png", "End the visual story with the limitation.", accent=GREEN)

    add_text_card(fig, [0.025, 0.07, 0.95, 0.10], 9, "Reproducibility footer", "List the frozen moduli, roots, M values, sample count, seeds, uncertainty unit, and links to code/data. Move technical proof details to a handout if space is tight.", accent=NAVY, facecolor=PALE_BLUE)
    add_footer(fig, "Recommended when the audience has heard of Shor's algorithm but has not studied Regev-style factoring.")
    return fig


def save(fig, stem):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    # The layout is composed on a 16:12 working canvas, then uniformly enlarged
    # to a true 48 x 36 inch page.  Scaling type and strokes preserves the exact
    # proportions seen in the quick preview while making PDF/SVG dimensions
    # correct for the requested poster size.
    fig.set_size_inches(48, 36, forward=True)
    for text_artist in fig.findobj(match=Text):
        text_artist.set_fontsize(text_artist.get_fontsize() * 3)
    for patch_artist in fig.findobj(match=Patch):
        patch_artist.set_linewidth(patch_artist.get_linewidth() * 3)
    for line_artist in fig.findobj(match=Line2D):
        line_artist.set_linewidth(line_artist.get_linewidth() * 3)
    for extension in ("png", "svg", "pdf"):
        kwargs = {"facecolor": fig.get_facecolor()}
        if extension == "png":
            kwargs["dpi"] = 50
        fig.savefig(OUTPUT / f"{stem}.{extension}", **kwargs)
    plt.close(fig)


def main():
    save(option_a_story_first(), "L01_story_first_48x36_LAYOUT_MOCKUP")
    save(option_b_result_first(), "L02_result_first_48x36_LAYOUT_MOCKUP")
    save(option_c_beginner_first(), "L03_beginner_first_48x36_LAYOUT_MOCKUP")
    print(f"Wrote 3 poster layout options in PNG, SVG, and PDF to {OUTPUT}")


if __name__ == "__main__":
    main()
