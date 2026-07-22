#!/usr/bin/env python3
"""Generate a large, evidence-labeled poster-graphics library.

Every quantitative figure reads the frozen qft-certificate-gap CSV files.
Conceptual diagrams are explicitly labeled as schematics.  The script never
uses known factors for an experimental calculation; factor pairs are shown
only as beginner-facing explanatory labels for already-frozen semiprimes.
"""
from __future__ import annotations

import csv
import math
import textwrap
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle
from PIL import Image, ImageDraw, ImageFont, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "poster graphics"
DATA = ROOT / "results" / "qft_certificate_gap"

NAVY = "#13294B"
ORANGE = "#FF5F05"
BLUE = "#0072B2"
CYAN = "#28A9C7"
PURPLE = "#7E57C2"
TEAL = "#009E73"
CREAM = "#FFFDF7"
INK = "#15243A"
MUTED = "#5D6B7E"
PALE_BLUE = "#E9F5FA"
PALE_ORANGE = "#FFF0E8"
PALE_PURPLE = "#F0ECFA"
PALE_TEAL = "#E7F5F0"
RED = "#C23B3B"
GOLD = "#E6A700"

mpl.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.titleweight": "bold",
    "axes.titlesize": 20,
    "axes.labelsize": 12,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "figure.facecolor": CREAM,
    "axes.facecolor": CREAM,
    "savefig.facecolor": CREAM,
    "svg.fonttype": "none",
})

MANIFEST: list[dict[str, str]] = []


def read_csv(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(newline="") as f:
        return list(csv.DictReader(f))


PAIRED = read_csv("paired_cluster_rows.csv")
PER_N = read_csv("per_N_rows.csv")
MARGINS = read_csv("margin_summary_rows.csv")
CONFIG = read_csv("configuration_rows.csv")
SLACK = read_csv("proof_slack_rows.csv")
LOO = read_csv("leave_one_N_out_rows.csv")


def newfig(w=12, h=7, dark=False):
    fig, ax = plt.subplots(figsize=(w, h))
    bg = NAVY if dark else CREAM
    fig.patch.set_facecolor(bg)
    ax.set_facecolor(bg)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return fig, ax


def rounded(ax, xy, w, h, fc="white", ec="none", lw=1.5, radius=0.025, alpha=1.0):
    p = FancyBboxPatch(xy, w, h, boxstyle=f"round,pad=0.012,rounding_size={radius}",
                       facecolor=fc, edgecolor=ec, linewidth=lw, alpha=alpha)
    ax.add_patch(p)
    return p


def txt(ax, x, y, s, size=18, color=INK, weight="normal", ha="left", va="center",
        wrap=None, family=None, zorder=5, linespacing=1.2):
    if wrap:
        s = "\n".join(textwrap.wrap(str(s), wrap))
    return ax.text(x, y, s, fontsize=size, color=color, weight=weight, ha=ha, va=va,
                   family=family, zorder=zorder, linespacing=linespacing)


def arrow(ax, p1, p2, color=CYAN, lw=3, style="-|>", connectionstyle="arc3"):
    a = FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=17, linewidth=lw,
                        color=color, connectionstyle=connectionstyle, zorder=4)
    ax.add_patch(a)
    return a


def footer(ax, evidence: str, dark=False):
    color = "#BDD0E4" if dark else MUTED
    txt(ax, .02, .025, evidence.upper(), 8.5, color, "bold", va="bottom")


def save(fig, folder, stem, title, evidence, caption, source, formats=("png", "svg")):
    dest = OUT / folder
    dest.mkdir(parents=True, exist_ok=True)
    for ext in formats:
        fig.savefig(dest / f"{stem}.{ext}", dpi=220 if ext == "png" else None,
                    bbox_inches="tight", pad_inches=.12, facecolor=fig.get_facecolor())
    plt.close(fig)
    MANIFEST.append({
        "id": stem,
        "folder": folder,
        "title": title,
        "evidence_level": evidence,
        "caption": caption,
        "source": source,
        "files": f"{stem}.png; {stem}.svg",
    })


def titlebar(ax, title, subtitle=None, dark=False):
    c = "white" if dark else NAVY
    txt(ax, .04, .92, title, 25, c, "bold", va="top")
    if subtitle:
        txt(ax, .04, .84, subtitle, 11.5, "#BFD4E5" if dark else MUTED, va="top", wrap=110)


def stat_card(ax, x, y, w, h, number, label, color=BLUE, dark=False):
    rounded(ax, (x, y), w, h, fc="#1B365D" if dark else "white",
            ec="#36587B" if dark else "#D9E3EA", lw=1.2)
    txt(ax, x+w/2, y+h*.61, number, min(32, 16+w*40), color, "bold", ha="center")
    txt(ax, x+w/2, y+h*.25, label, 10, "#DCE7F1" if dark else MUTED,
        "bold", ha="center", wrap=max(10, int(w*70)))


def generic_statement(folder, stem, eyebrow, headline, body, accent, evidence, caption, source,
                      number=None, dark=False):
    fig, ax = newfig(12, 6.75, dark)
    fg = "white" if dark else NAVY
    muted = "#C4D3E1" if dark else MUTED
    txt(ax, .06, .88, eyebrow.upper(), 11, accent, "bold", va="top")
    if number:
        # Reserve a distinct right-hand metric zone.  Keeping the headline in
        # the left 65% prevents long titles from colliding with large numbers.
        txt(ax, .06, .78, headline, 29, fg, "bold", va="top", wrap=24, linespacing=1.04)
        rounded(ax, (.76, .53), .18, .18,
                fc="#203D65" if dark else "white", ec=accent, lw=2, radius=.03)
        metric_size = 18 if len(str(number)) > 7 else (28 if len(str(number)) > 4 else 36)
        txt(ax, .85, .62, number, metric_size, accent, "bold", ha="center")
    else:
        txt(ax, .06, .78, headline, 34, fg, "bold", va="top", wrap=35, linespacing=1.06)
    rounded(ax, (.055, .16), .89, .28, fc="#1C385F" if dark else "white",
            ec="#36587B" if dark else "#DCE4EB")
    txt(ax, .09, .30, body, 16, muted, va="center", wrap=82, linespacing=1.35)
    footer(ax, evidence, dark)
    save(fig, folder, stem, headline, evidence, caption, source)


def simple_flow(folder, stem, title, subtitle, steps, colors, evidence, caption, source, dark=False):
    fig, ax = newfig(14, 5.8, dark)
    titlebar(ax, title, subtitle, dark)
    n = len(steps)
    margin, gap = .04, .025
    w = (1-2*margin-gap*(n-1))/n
    y, h = .25, .34
    for i, (heading, detail) in enumerate(steps):
        x = margin+i*(w+gap)
        rounded(ax, (x,y), w,h, fc="#1B365D" if dark else "white",
                ec=colors[i%len(colors)], lw=2)
        ax.add_patch(Circle((x+.045,y+h-.055), .025, facecolor=colors[i%len(colors)], edgecolor="none"))
        txt(ax, x+.045, y+h-.055, str(i+1), 10, "white", "bold", ha="center")
        txt(ax, x+.03, y+h-.12, heading, 13, "white" if dark else NAVY, "bold", va="top", wrap=max(12,int(w*62)))
        txt(ax, x+.03, y+h-.21, detail, 9.5, "#C7D8E7" if dark else MUTED, va="top", wrap=max(13,int(w*67)))
        if i<n-1:
            arrow(ax, (x+w+.002,y+h/2), (x+w+gap-.003,y+h/2), colors[(i+1)%len(colors)], 2)
    footer(ax, evidence, dark)
    save(fig, folder, stem, title, evidence, caption, source)


# ---------------------------------------------------------------------------
# 01 — headline cards
# ---------------------------------------------------------------------------
generic_statement(
    "01_HEADLINE_CARDS", "H01_project_title", "Research finding",
    "A QFT certificate can reject a cutoff that the full decoder still tolerates",
    "We test Fourier truncation at the actual endpoint: samples → exact integer lattice → LLL → verified relation → factor.",
    CYAN, "Verified framing; frozen experiment", "Project-title lockup for the top of a poster.",
    "latex_short_paper/main.tex; results/qft_certificate_gap/configuration.json", dark=True)

generic_statement(
    "01_HEADLINE_CARDS", "H02_one_layer_result", "Main held-out result",
    "One omitted QFT layer passed in every tested model–modulus cell",
    "At the preregistered 10-percentage-point non-inferiority margin: 6 of 6 cells passed across M = 8, 16, 32 and two exact finite state models.",
    TEAL, "Verified frozen empirical result", "Primary one-layer finding; N is the unit of generalization.",
    "results/qft_certificate_gap/certificate_gap_rows.csv; paired_cluster_rows.csv", number="6 / 6", dark=True)

generic_statement(
    "01_HEADLINE_CARDS", "H03_two_layer_qualified", "Qualified result",
    "Two omitted layers passed only in the finite-Gaussian model at M = 16 and 32",
    "This is model- and parameter-specific evidence. It is not a claim for the full asymptotic Regev algorithm or hardware.",
    PURPLE, "Verified frozen empirical result", "Use beside the main result to prevent overgeneralization.",
    "results/qft_certificate_gap/certificate_gap_rows.csv", number="2 / 6", dark=True)

generic_statement(
    "01_HEADLINE_CARDS", "H04_qft_savings_hero", "Largest passing tested cutoff · M = 32",
    "6 controlled phases and 12 transpiled CX gates removed",
    "Exact: 20 CP / 52 CX / depth 36. Two-layer omission: 14 CP / 40 CX / depth 36. These are QFT-only counts.",
    ORANGE, "Verified compiled QFT-only resource result", "Largest observed passing QFT-only saving, finite-Gaussian M=32.",
    "results/qft_certificate_gap/configuration_rows.csv", number="−12 CX", dark=True)


def evidence_snapshot():
    fig, ax = newfig(12, 6.5)
    titlebar(ax, "Evidence at a glance", "Frozen before held-out evaluation; no modulus-specific tuning.")
    cards = [("8", "held-out semiprimes", BLUE), ("2", "exact finite state models", PURPLE),
             ("3", "Fourier moduli", CYAN), ("64", "coupled replicates per cell", TEAL),
             ("12,288", "endpoint trials", ORANGE), ("5,000", "cluster bootstrap draws", GOLD)]
    for i,c in enumerate(cards):
        row,col=divmod(i,3); stat_card(ax,.05+col*.31,.49-row*.26,.27,.20,*c)
    footer(ax,"Verified frozen experiment inventory")
    save(fig,"01_HEADLINE_CARDS","H05_evidence_snapshot","Evidence at a glance",
         "Verified frozen experiment inventory","Compact numeric overview.",
         "results/qft_certificate_gap/configuration.json")
evidence_snapshot()

generic_statement(
    "01_HEADLINE_CARDS", "H06_claim_boundary", "The exact claim boundary",
    "A finite certification gap — not a universal approximate-QFT theorem",
    "Verified for eight small semiprimes, d = 2, m = 7, M ≤ 32, two exact finite models, and the current LLL decoder. No end-to-end hardware speedup is claimed.",
    RED, "Verified scope statement", "A prominent limitation card for responsible poster wording.",
    "latex_short_paper/main.tex; results/qft_certificate_gap/configuration.json", dark=False)

# ---------------------------------------------------------------------------
# 02 — beginner background
# ---------------------------------------------------------------------------
def shor_regev():
    fig, ax = newfig(13, 7)
    titlebar(ax,"Shor and Regev: two ways to turn quantum structure into factors",
             "Descriptive tradeoff only — this graphic does not claim a measured speedup.")
    for x, title, col, items in [
        (.05,"Shor-style",BLUE,["Quantum period finding","One-dimensional Fourier structure","Continued-fraction decoding"]),
        (.53,"Regev-style",PURPLE,["Multidimensional Fourier samples","More quantum circuit executions","Classical lattice decoding (LLL)"])]:
        rounded(ax,(x,.2),.42,.52,"white",col,2)
        txt(ax,x+.04,.65,title,22,col,"bold",va="top")
        for j,item in enumerate(items):
            ax.add_patch(Circle((x+.06,.53-j*.12),.018,facecolor=col,edgecolor="none"))
            txt(ax,x+.095,.53-j*.12,item,13,INK,"bold",wrap=30)
    arrow(ax,(.46,.46),(.52,.46),ORANGE,3,style="<->")
    txt(ax,.49,.36,"different\nquantum/classical\ntradeoff",10,ORANGE,"bold",ha="center")
    footer(ax,"Conceptual background; not an empirical comparison")
    save(fig,"02_BEGINNER_BACKGROUND","B01_shor_vs_regev","Shor vs. Regev tradeoff",
         "Conceptual background","Beginner-friendly comparison; no speedup claim.",
         "Shor (1994/1997); Regev (2023/2025)")
shor_regev()

simple_flow("02_BEGINNER_BACKGROUND","B02_regev_one_picture","Regev-style factoring in one picture",
            "The quantum stage creates structured samples; the classical stage searches for an arithmetic relation.",
            [("Choose roots","Keep each bᵢ paired with aᵢ=bᵢ² mod N"),("Quantum sample","Prepare exponents, compute modular product, apply inverse QFT"),("Build lattice","Encode measured rows in an augmented integer lattice"),("Reduce","Run exact-integer LLL and inspect candidates"),("Verify + factor","Check z∈L, then use stored roots and gcd")],
            [ORANGE,CYAN,BLUE,PURPLE,TEAL],"Conceptual schematic of implemented endpoint",
            "Horizontal full-pipeline explainer.","latex_short_paper/main.tex; regev_research/")

def qft_lens():
    fig, ax=newfig(12,6.5,dark=True); titlebar(ax,"The QFT is a frequency lens","It converts repeating phase structure into concentrated measurement peaks.",True)
    x=np.linspace(0,1,250); wave=.12*np.sin(2*np.pi*7*x)
    ax.plot(.05+.36*x,.48+wave,color=CYAN,lw=3)
    txt(ax,.23,.27,"structured amplitudes",13,"white","bold",ha="center")
    rounded(ax,(.45,.32),.13,.30,"#213E67",ORANGE,2); txt(ax,.515,.47,"QFT⁻¹",24,ORANGE,"bold",ha="center")
    arrow(ax,(.40,.48),(.45,.48),ORANGE); arrow(ax,(.58,.48),(.63,.48),ORANGE)
    bars=[.15,.22,.78,.26,.12,.55,.18,.1]
    for i,v in enumerate(bars): ax.add_patch(Rectangle((.64+i*.038,.34),.025,.32*v,facecolor=PURPLE if v>.5 else CYAN,edgecolor="none"))
    txt(ax,.80,.27,"measured frequencies",13,"white","bold",ha="center")
    footer(ax,"Conceptual schematic",True)
    save(fig,"02_BEGINNER_BACKGROUND","B03_qft_frequency_lens","QFT as a frequency lens","Conceptual schematic","Beginner QFT intuition.","Standard QFT interpretation")
qft_lens()

def exact_approx():
    fig,ax=newfig(12,6.5); titlebar(ax,"Exact vs. truncated inverse QFT","Truncation removes the smallest controlled rotations.")
    for row,(label,count,col) in enumerate([("Exact QFT",4,BLUE),("Omit one layer",3,TEAL),("Omit two layers",2,ORANGE)]):
        y=.67-row*.20; txt(ax,.06,y,label,14,col,"bold")
        ax.plot([.23,.91],[y,y],color="#CCD7E0",lw=2)
        for j in range(4):
            on=j<count
            ax.add_patch(Circle((.34+j*.15,y),.035,facecolor=col if on else CREAM,edgecolor=col if on else "#CCD7E0",lw=2))
            txt(ax,.34+j*.15,y,f"R{j+2}",8,"white" if on else MUTED,"bold",ha="center")
    txt(ax,.50,.16,"fewer phase gates  →  lower QFT cost  →  possible recovery loss",13,NAVY,"bold",ha="center")
    footer(ax,"Conceptual schematic; layer count is illustrative")
    save(fig,"02_BEGINNER_BACKGROUND","B04_exact_vs_truncated_qft","Exact vs. truncated QFT","Conceptual schematic","Explains what a QFT cutoff changes.","regev_research/qft_certificate.py")
exact_approx()

def relation_factor():
    fig,ax=newfig(12,6.4); titlebar(ax,"How a recovered relation becomes a factor","The final arithmetic check uses the stored roots bᵢ — never arbitrary square roots.")
    steps=[("LLL candidate","z ∈ ℤᵈ",BLUE),("Verify relation","∏ aᵢᶻⁱ ≡ 1 (mod N)",PURPLE),("Lift with roots","β=∏ bᵢᶻⁱ (mod N)",ORANGE),("Useful if β≠±1","gcd(β±1,N)",TEAL)]
    for i,(h,d,c) in enumerate(steps):
        x=.04+i*.24; rounded(ax,(x,.30),.20,.32,"white",c,2); txt(ax,x+.10,.54,h,13,c,"bold",ha="center",wrap=18); txt(ax,x+.10,.41,d,14,INK,"bold",ha="center",wrap=18)
        if i<3: arrow(ax,(x+.205,.46),(x+.235,.46),CYAN,2)
    footer(ax,"Implemented mathematical endpoint")
    save(fig,"02_BEGINNER_BACKGROUND","B05_relation_to_factor","Relation to factor","Implemented mathematical endpoint","Beginner factor-extraction explainer.","latex_short_paper/main.tex; regev_research/lattice.py")
relation_factor()

def roots_bases():
    fig,ax=newfig(11,6.5); titlebar(ax,"Roots and circuit bases are different objects","Root provenance is required metadata, not optional bookkeeping.")
    for i,(b,a) in enumerate([(2,"4 mod N"),(3,"9 mod N")]):
        y=.65-i*.25
        rounded(ax,(.09,y-.08),.20,.16,PALE_ORANGE,ORANGE,2); txt(ax,.19,y,f"root  b{i+1} = {b}",15,ORANGE,"bold",ha="center")
        arrow(ax,(.30,y),(.44,y),ORANGE); txt(ax,.37,y+.06,"square mod N",9,MUTED,"bold",ha="center")
        rounded(ax,(.45,y-.08),.22,.16,PALE_BLUE,BLUE,2); txt(ax,.56,y,f"base  a{i+1} = {a}",15,BLUE,"bold",ha="center")
        arrow(ax,(.68,y),(.84,y),PURPLE); txt(ax,.90,y,"stored pair",12,PURPLE,"bold",ha="center")
    footer(ax,"Verified implementation requirement")
    save(fig,"02_BEGINNER_BACKGROUND","B06_roots_and_bases","Stored roots and squared bases","Verified implementation requirement","Root-provenance explainer.","ROOT_PROVENANCE_RED_TEAM.md; latex_short_paper/main.tex")
roots_bases()

# ---------------------------------------------------------------------------
# 03 — pipeline
# ---------------------------------------------------------------------------
simple_flow("03_PIPELINE","P01_full_endpoint","The tested endpoint","Every reported success reaches an actual factor.",
            [("Sample","Exact finite Fourier law"),("Augment","Clear denominators exactly"),("LLL","Exact integer reduction"),("Candidate z","Read first d transform coefficients"),("Membership","Verify z∈L and test L₀"),("Factor","gcd with stored-root lift")],
            [CYAN,BLUE,PURPLE,PURPLE,ORANGE,TEAL],"Verified implemented workflow","Detailed pipeline strip.","latex_short_paper/main.tex; regev_research/lattice.py")

def quantum_classical_split():
    fig,ax=newfig(13,6.5); titlebar(ax,"Where the quantum part ends — and the evidence begins",None)
    rounded(ax,(.04,.24),.43,.50,PALE_BLUE,CYAN,2); rounded(ax,(.53,.24),.43,.50,PALE_PURPLE,PURPLE,2)
    txt(ax,.255,.66,"QUANTUM / EXACT SIMULATOR",16,CYAN,"bold",ha="center")
    txt(ax,.255,.50,"prepare → modular arithmetic → QFT⁻¹ → measure",15,NAVY,"bold",ha="center",wrap=35)
    txt(ax,.745,.66,"CLASSICAL DECODER",16,PURPLE,"bold",ha="center")
    txt(ax,.745,.50,"samples → augmented lattice → LLL → verify → gcd",15,NAVY,"bold",ha="center",wrap=35)
    arrow(ax,(.47,.49),(.53,.49),ORANGE,4); txt(ax,.50,.37,"k ∈ [M]ᵈ",11,ORANGE,"bold",ha="center")
    footer(ax,"Conceptual schematic of the implemented pipeline")
    save(fig,"03_PIPELINE","P02_quantum_classical_split","Quantum/classical split","Conceptual schematic of implemented pipeline","Useful center-panel bridge graphic.","latex_short_paper/main.tex")
quantum_classical_split()

simple_flow("03_PIPELINE","P03_samples_to_lattice","Samples become an exact integer lattice",
            "The implementation clears rational denominators before reduction; no unsupported floating projection.",
            [("Rows kⱼ","m measured vectors in [M]ᵈ"),("Matrix K","stack samples"),("Scale S","encode expected noise"),("Integer basis A","clear M and rational scale"),("LLL transform","candidate coefficients reveal z")],
            [CYAN,CYAN,ORANGE,BLUE,PURPLE],"Verified implementation schematic","Sample-to-lattice construction.","latex_short_paper/main.tex, Eq. (5)")

simple_flow("03_PIPELINE","P04_stored_root_endpoint","The stored-root factor endpoint",None,
            [("Candidate z","from LLL transform"),("Check L","∏aᵢᶻⁱ=1 mod N"),("Compute β","∏bᵢᶻⁱ mod N"),("Check L₀","β=±1 is valid but useless"),("Extract","β≠±1 → gcd(β±1,N)")],
            [PURPLE,BLUE,ORANGE,RED,TEAL],"Verified implementation schematic","Candidate classification and factor endpoint.","latex_short_paper/main.tex; ROOT_PROVENANCE_RED_TEAM.md")

simple_flow("03_PIPELINE","P05_data_dependency","Evidence dependency graph",None,
            [("Frozen protocol","N, roots, M, models, m, seed"),("Finite laws","exact and each cutoff"),("Coupled draws","same uniforms across cutoffs"),("Decoder","same integer LLL endpoint"),("N-level deltas","paired success differences"),("Decision","cluster bootstrap vs −0.10")],
            [NAVY,CYAN,BLUE,PURPLE,ORANGE,TEAL],"Verified frozen analysis flow","Shows how inputs become the primary claim.","results/qft_certificate_gap/configuration.json; paired_cluster_rows.csv")

# ---------------------------------------------------------------------------
# 04 — certificate mechanism
# ---------------------------------------------------------------------------
simple_flow("04_CERTIFICATE_AND_FIBERS","C01_certificate_chain","What the original certificate bounds",
            "Each conservative step forgets some task-specific structure.",
            [("Omitted angles","sum phase magnitudes"),("Operator error","worst over all inputs"),("d registers","tensor triangle bound"),("Measurement TV","data processing"),("m samples","product / hybrid bound"),("Factor event","any decoder event")],
            [ORANGE,RED,PURPLE,BLUE,CYAN,TEAL],"Verified proof audit schematic","Line-by-line certificate chain.","QFT_CERTIFICATE_PROOF_AUDIT.md; latex_short_paper/main.tex")

def worst_prepared():
    fig,ax=newfig(12,6.6); titlebar(ax,"Worst-case unitary error is not prepared-state recovery loss",None)
    ax.add_patch(Circle((.35,.48),.28,facecolor=PALE_ORANGE,edgecolor=ORANGE,lw=3)); ax.add_patch(Circle((.35,.48),.11,facecolor=PALE_TEAL,edgecolor=TEAL,lw=3))
    txt(ax,.35,.70,"all possible input states",14,ORANGE,"bold",ha="center")
    txt(ax,.35,.48,"prepared\nfiber state",13,TEAL,"bold",ha="center")
    arrow(ax,(.63,.48),(.78,.48),PURPLE,4)
    rounded(ax,(.79,.32),.17,.32,"white",PURPLE,2); txt(ax,.875,.57,"decoder event",13,PURPLE,"bold",ha="center"); txt(ax,.875,.43,"success / failure",12,INK,"bold",ha="center")
    txt(ax,.62,.27,"restriction + measurement can cancel error",12,MUTED,"bold",ha="center")
    footer(ax,"Mechanism established analytically; not a universal performance guarantee")
    save(fig,"04_CERTIFICATE_AND_FIBERS","C02_worst_case_vs_prepared","Worst case vs prepared state","Analytical mechanism","Explains the certification gap.","QFT_CERTIFICATE_PROOF_AUDIT.md")
worst_prepared()

def fibers():
    fig,ax=newfig(12,6.6,dark=True); titlebar(ax,"Fiber cancellation: different paths, same measured law","Modular arithmetic groups exponent strings into fibers before the QFT outcome is read.",True)
    pts=[(.12,.64),(.12,.49),(.12,.34)]; cols=[CYAN,PURPLE,ORANGE]
    for i,p in enumerate(pts):
        ax.add_patch(Circle(p,.035,facecolor=cols[i],edgecolor="white",lw=1)); txt(ax,p[0]-.06,p[1],f"x{i+1}",11,"white","bold",ha="right")
        arrow(ax,(p[0]+.04,p[1]),(.45,.50),cols[i],2,connectionstyle=f"arc3,rad={(i-1)*.18}")
    rounded(ax,(.43,.38),.20,.24,"#1E3A62",CYAN,2); txt(ax,.53,.50,"same arithmetic\nresidue y",15,"white","bold",ha="center")
    arrow(ax,(.64,.50),(.79,.50),ORANGE,3)
    ax.add_patch(Circle((.86,.50),.09,facecolor=PALE_TEAL,edgecolor=TEAL,lw=3)); txt(ax,.86,.50,"|Σ phase|²",15,TEAL,"bold",ha="center")
    txt(ax,.52,.20,"Omitted phases may cancel inside the coherent sum over each fiber.",14,"white","bold",ha="center")
    footer(ax,"Analytical mechanism from exact finite measurement law",True)
    save(fig,"04_CERTIFICATE_AND_FIBERS","C03_fiber_cancellation","Fiber cancellation","Analytical mechanism","Hero mechanism diagram.","latex_short_paper/main.tex, Eq. (4)")
fibers()

generic_statement("04_CERTIFICATE_AND_FIBERS","C04_n15_counterexample","Controlled counterexample · N = 15",
                  "Certificate rejects — measured distributions are identical",
                  "With squared bases (4,1), d=2, M=4, and cutoff 0, the exact finite total-variation distance is 5.9×10⁻³⁵. This refutes an implication; it is not a benchmark.",
                  ORANGE,"Verified controlled example","Explicit equal-law counterexample.","results/qft_certificate_gap/controlled_examples.json",number="TV ≈ 0",dark=True)

def certificate_barrier():
    fig,ax=newfig(12,6.5); titlebar(ax,"Why the certificate selects exact QFT in this finite regime",None)
    x=np.logspace(1,4,300); ax.axis("on"); ax.set_xlim(10,10000); ax.set_xscale("log"); ax.set_ylim(0,1); ax.set_yticks([]); ax.set_xlabel("Fourier modulus M (log scale)")
    ax.axvspan(10,32,color=PALE_ORANGE); ax.axvline(3518.6,color=RED,lw=3,ls="--"); ax.axvspan(3518.6,10000,color=PALE_TEAL)
    ax.text(20,.62,"tested\nM ≤ 32",ha="center",va="center",fontsize=18,color=ORANGE,weight="bold")
    ax.text(3518.6,.82,"necessary threshold ≈ 3518.6",ha="center",fontsize=13,color=RED,weight="bold")
    ax.text(6000,.48,"non-exact cutoff may become\ncertifiable (not guaranteed)",ha="center",fontsize=13,color=TEAL,weight="bold")
    ax.text(150,.27,"certificate forces exact QFT",ha="center",fontsize=15,color=NAVY,weight="bold")
    ax.spines[["top","left","right"]].set_visible(False); ax.grid(axis="x",alpha=.15)
    fig.text(.02,.02,"VERIFIED PROOF-AUDIT CONSEQUENCE · d=2, m=7, Δ=0.05",fontsize=8.5,color=MUTED,weight="bold")
    save(fig,"04_CERTIFICATE_AND_FIBERS","C05_certificate_barrier","Finite certificate barrier","Verified proof-audit consequence","Visualizes M < 4πdm/Δ with frozen d,m,Δ.","latex_short_paper/main.tex, Proposition 1")
certificate_barrier()

def evidence_levels():
    fig,ax=newfig(10,7); titlebar(ax,"Three different questions — three different answers",None)
    cards=[("CERTIFICATE","Is every downstream event protected?","No non-exact cutoff approved",RED),
           ("FINITE DISTRIBUTION","How much does this prepared measurement law change?","Sometimes far less than the worst-case bound",CYAN),
           ("FACTOR ENDPOINT","Does the tested decoder still recover factors?","One layer passed all six held-out cells",TEAL)]
    for i,(h,q,a,c) in enumerate(cards):
        y=.66-i*.22; rounded(ax,(.06,y-.13),.88,.18,"white",c,2); txt(ax,.09,y+.01,h,10,c,"bold"); txt(ax,.25,y+.01,q,12,INK,"bold"); txt(ax,.25,y-.07,a,11,c,"bold")
    footer(ax,"Verified distinction between guarantee, distribution, and endpoint")
    save(fig,"04_CERTIFICATE_AND_FIBERS","C06_three_questions","Certificate vs distribution vs endpoint","Verified explanatory synthesis","Separates three common claims.","QFT_CERTIFICATE_PROOF_AUDIT.md; certificate_gap_rows.csv")
evidence_levels()

# ---------------------------------------------------------------------------
# 05 — frozen experiment
# ---------------------------------------------------------------------------
simple_flow("05_FROZEN_EXPERIMENT","E01_frozen_protocol","Frozen held-out protocol",
            "All moduli, roots, parameters, seeds, reduction rules, and stopping criteria were fixed before evaluation.",
            [("Freeze","version qft-certificate-gap-v1"),("Hold out N","8 semiprimes"),("Cross models","hard box + finite Gaussian"),("Cross M","8, 16, 32"),("Pair draws","64 coupled replicates"),("Cluster by N","5,000 bootstrap draws")],
            [NAVY,BLUE,PURPLE,CYAN,ORANGE,TEAL],"Verified frozen design","Protocol overview.","results/qft_certificate_gap/configuration.json")

def heldout():
    fig,ax=newfig(13,6.2); titlebar(ax,"Eight held-out semiprimes","The modulus N — not repeated shots — is the primary unit of generalization.")
    vals=[55,65,85,95,115,119,133,161]; fac=["5×11","5×13","5×17","5×19","5×23","7×17","7×19","7×23"]
    for i,(n,f) in enumerate(zip(vals,fac)):
        x=.055+i*.116; ax.add_patch(Circle((x+.045,.49),.047,facecolor=[BLUE,CYAN,PURPLE,ORANGE,TEAL,GOLD,BLUE,PURPLE][i],edgecolor="none")); txt(ax,x+.045,.49,str(n),13,"white","bold",ha="center"); txt(ax,x+.045,.38,f,10,MUTED,"bold",ha="center")
    txt(ax,.50,.20,"Factors shown here only as explanatory labels; selection and tuning were factor-blind.",11,INK,"bold",ha="center")
    footer(ax,"Verified frozen modulus list")
    save(fig,"05_FROZEN_EXPERIMENT","E02_heldout_moduli","Held-out semiprimes","Verified frozen design","Complete held-out N list.","results/qft_certificate_gap/configuration.json")
heldout()

def design_grid():
    fig,ax=newfig(11,7); titlebar(ax,"A 3 × 2 primary comparison grid",None)
    models=["Uniform hard-box\n(Model A)","Finite discrete Gaussian\n(Model B)"]; ms=[8,16,32]
    for i,m in enumerate(ms): txt(ax,.38+i*.20,.70,f"M = {m}",14,NAVY,"bold",ha="center")
    for r,model in enumerate(models):
        y=.53-r*.23; txt(ax,.08,y,model,13,[BLUE,PURPLE][r],"bold",wrap=18)
        for c,m in enumerate(ms):
            rounded(ax,(.30+c*.20,y-.08),.16,.16,[PALE_BLUE,PALE_PURPLE][r],[BLUE,PURPLE][r],2); txt(ax,.38+c*.20,y,"8 N × 64\npaired draws",11,[BLUE,PURPLE][r],"bold",ha="center")
    txt(ax,.50,.15,"Every cutoff compared with exact QFT using coupled random draws",12,TEAL,"bold",ha="center")
    footer(ax,"Verified frozen factorial design")
    save(fig,"05_FROZEN_EXPERIMENT","E03_design_grid","Primary experiment grid","Verified frozen design","Six primary model–M cells.","results/qft_certificate_gap/configuration.json")
design_grid()

generic_statement("05_FROZEN_EXPERIMENT","E04_unit_generalization","Statistics",
                  "N is the unit of generalization",
                  "Success is paired within each modulus, then aggregated across eight N clusters. Repeated replicates improve each N estimate; they do not create 12,288 independent moduli.",
                  BLUE,"Verified statistical design","Prevents pseudoreplication in poster interpretation.","results/qft_certificate_gap/paired_cluster_rows.csv",number="8 N",dark=False)

def noninferiority():
    fig,ax=newfig(12,6.2); titlebar(ax,"How the non-inferiority decision works","Primary margin: 10 percentage points, frozen before held-out evaluation.")
    ax.plot([.08,.92],[.47,.47],color=NAVY,lw=3); ax.axvspan(.08,.35,ymin=.39,ymax=.56,color=PALE_ORANGE); ax.axvspan(.35,.92,ymin=.39,ymax=.56,color=PALE_TEAL)
    ax.plot([.35,.35],[.38,.58],color=RED,lw=3); txt(ax,.35,.64,"−0.10",14,RED,"bold",ha="center"); txt(ax,.64,.55,"PASS if cluster CI lower bound ≥ −0.10",14,TEAL,"bold",ha="center"); txt(ax,.19,.38,"too much loss",12,ORANGE,"bold",ha="center"); txt(ax,.92,.38,"0 = exact tie",11,NAVY,"bold",ha="right")
    footer(ax,"Verified preregistered decision rule")
    save(fig,"05_FROZEN_EXPERIMENT","E05_noninferiority_ruler","Non-inferiority rule","Verified frozen decision rule","Explains the 0.10 margin.","results/qft_certificate_gap/configuration.json")
noninferiority()

generic_statement("05_FROZEN_EXPERIMENT","E06_freeze_seed","Reproducibility",
                  "One frozen version. One master seed. Every row retained.",
                  "Freeze: qft-certificate-gap-v1 · Master seed: 2026071301 · 12,288 trial rows · known factors used only post hoc.",
                  CYAN,"Verified reproducibility metadata","Seed/freeze card.","results/qft_certificate_gap/configuration.json",number="2026071301",dark=True)

# ---------------------------------------------------------------------------
# 06 — primary results
# ---------------------------------------------------------------------------
def heatmap_primary():
    fig,ax=plt.subplots(figsize=(10,5.8)); fig.patch.set_facecolor(CREAM); ax.set_facecolor(CREAM)
    models=["A · hard box","B · finite Gaussian"]; ms=[8,16,32]; vals=np.array([[1,1,1],[1,2,2]])
    im=ax.imshow(vals,cmap=mpl.colors.ListedColormap([PALE_BLUE,PALE_PURPLE,TEAL]),vmin=0,vmax=2,aspect="auto")
    for r in range(2):
        for c in range(3): ax.text(c,r,f"{vals[r,c]} layer{'s' if vals[r,c]!=1 else ''}",ha="center",va="center",fontsize=20,weight="bold",color=NAVY)
    ax.set_xticks(range(3),[f"M = {m}" for m in ms]); ax.set_yticks(range(2),models); ax.set_title("Largest omission passing the frozen 0.10 margin",pad=18,color=NAVY)
    for s in ax.spines.values(): s.set_visible(False)
    fig.text(.02,.015,"VERIFIED HELD-OUT RESULT · 8 N clusters · 64 coupled replicates per cell",fontsize=8.5,color=MUTED,weight="bold")
    save(fig,"06_PRIMARY_RESULTS","R01_primary_heatmap","Largest passing omission","Verified frozen empirical result","Primary result heatmap.","results/qft_certificate_gap/certificate_gap_rows.csv")
heatmap_primary()

def paired_forest():
    rows=[r for r in PAIRED if float(r["margin"])==.1 and int(r["omitted_layers"])>0]
    labels=[]; means=[]; lows=[]; highs=[]; cols=[]
    for r in rows:
        labels.append(f"M{r['M']} · {'A' if r['model'].startswith('A') else 'B'} · omit {r['omitted_layers']}")
        means.append(float(r["factor_mean_difference"])); lows.append(float(r["factor_cluster_ci95_low"])); highs.append(float(r["factor_cluster_ci95_high"])); cols.append(TEAL if r["empirically_noninferior"]=="True" else ORANGE)
    fig,ax=plt.subplots(figsize=(10,10)); fig.patch.set_facecolor(CREAM); ax.set_facecolor(CREAM)
    y=np.arange(len(rows)); ax.axvspan(-.10,.03,color=PALE_TEAL); ax.axvline(-.10,color=RED,ls="--",lw=2,label="−0.10 margin"); ax.axvline(0,color=NAVY,lw=1)
    for i in range(len(rows)): ax.errorbar(means[i],y[i],xerr=[[means[i]-lows[i]],[highs[i]-means[i]]],fmt="o",color=cols[i],ecolor=cols[i],capsize=4,ms=7)
    ax.set_yticks(y,labels); ax.invert_yaxis(); ax.set_xlabel("paired factor-success difference: truncated − exact"); ax.set_title("Every tested omission: N-cluster mean and 95% interval",color=NAVY,pad=18); ax.grid(axis="x",alpha=.15); ax.spines[["top","right","left"]].set_visible(False); ax.legend(frameon=False,loc="lower right")
    fig.text(.02,.012,"VERIFIED HELD-OUT RESULT · green = non-inferior at the frozen 0.10 margin",fontsize=8.5,color=MUTED,weight="bold")
    save(fig,"06_PRIMARY_RESULTS","R02_all_paired_differences","Paired recovery differences","Verified frozen empirical result","Forest plot of all non-exact cutoffs.","results/qft_certificate_gap/paired_cluster_rows.csv")
paired_forest()

def recovery_curves(model,stem,color):
    fig,ax=plt.subplots(figsize=(10,6)); fig.patch.set_facecolor(CREAM); ax.set_facecolor(CREAM)
    for M,ls in zip([8,16,32],["-","--",":"]):
        rows=[r for r in PER_N if r["model"]==model and int(r["M"])==M]
        by={int(r["omitted_layers"]):[] for r in rows}
        for r in rows: by[int(r["omitted_layers"])].append(float(r["factor_probability"]))
        xs=sorted(by); ys=[np.mean(by[x]) for x in xs]
        ax.plot(xs,ys,marker="o",lw=3,ls=ls,label=f"M={M}")
    ax.set_xlabel("omitted QFT layers"); ax.set_ylabel("mean factor-recovery probability across N"); ax.set_ylim(0,1); ax.set_xticks(range(5)); ax.grid(alpha=.16); ax.legend(frameon=False); ax.spines[["top","right"]].set_visible(False)
    label="uniform hard-box" if model.startswith("A") else "finite discrete-Gaussian"
    ax.set_title(f"Recovery curve · {label} model",color=NAVY,pad=16)
    fig.text(.02,.015,"VERIFIED HELD-OUT RESULT · descriptive N-level mean; decisions use paired cluster intervals",fontsize=8.5,color=MUTED,weight="bold")
    save(fig,"06_PRIMARY_RESULTS",stem,f"Recovery curve: {label}","Verified frozen empirical result",f"Recovery vs omitted layers for {label}.","results/qft_certificate_gap/per_N_rows.csv")
recovery_curves("A_uniform_hard_box","R03_recovery_curve_model_A",BLUE)
recovery_curves("B_exact_finite_discrete_gaussian","R04_recovery_curve_model_B",PURPLE)

def per_n_omit1():
    fig,axs=plt.subplots(1,2,figsize=(13,6),sharey=True); fig.patch.set_facecolor(CREAM)
    for ax,model,title,col in zip(axs,["A_uniform_hard_box","B_exact_finite_discrete_gaussian"],["A · hard box","B · finite Gaussian"],[BLUE,PURPLE]):
        ex={int(r["N"]):float(r["factor_probability"]) for r in PER_N if r["model"]==model and int(r["M"])==32 and int(r["omitted_layers"])==0}
        ap={int(r["N"]):float(r["factor_probability"]) for r in PER_N if r["model"]==model and int(r["M"])==32 and int(r["omitted_layers"])==1}
        ns=sorted(ex); y=np.arange(len(ns)); ax.hlines(y,[ex[n] for n in ns],[ap[n] for n in ns],color="#C9D4DE",lw=3); ax.scatter([ex[n] for n in ns],y,color=NAVY,label="exact",s=45); ax.scatter([ap[n] for n in ns],y,color=col,label="omit 1",s=45)
        ax.set_yticks(y,ns); ax.set_xlabel("factor-recovery probability"); ax.set_title(title,color=col,weight="bold"); ax.grid(axis="x",alpha=.15); ax.spines[["top","right","left"]].set_visible(False); ax.legend(frameon=False)
    axs[0].set_ylabel("held-out modulus N"); fig.suptitle("M = 32: one-layer omission by held-out modulus",fontsize=20,weight="bold",color=NAVY)
    fig.text(.02,.01,"VERIFIED HELD-OUT RESULT · each point uses 64 coupled replicates",fontsize=8.5,color=MUTED,weight="bold")
    save(fig,"06_PRIMARY_RESULTS","R05_per_N_omit1_M32","Per-N one-layer comparison","Verified frozen empirical result","Exact vs one-layer omission for every held-out N at M=32.","results/qft_certificate_gap/per_N_rows.csv")
per_n_omit1()

def margin_sensitivity():
    fig,axs=plt.subplots(1,2,figsize=(12,5.8),sharey=True); fig.patch.set_facecolor(CREAM)
    for ax,model,title in zip(axs,["A_uniform_hard_box","B_exact_finite_discrete_gaussian"],["A · hard box","B · finite Gaussian"]):
        for M,col in zip([8,16,32],[BLUE,CYAN,PURPLE]):
            rows=sorted([r for r in MARGINS if r["model"]==model and int(r["M"])==M],key=lambda r:float(r["margin"]))
            ax.plot([float(r["margin"]) for r in rows],[int(r["largest_noninferior_omitted_layers"]) for r in rows],marker="o",lw=2.5,color=col,label=f"M={M}")
        ax.axvline(.10,color=ORANGE,ls="--",lw=2); ax.set_title(title,color=NAVY,weight="bold"); ax.set_xlabel("allowed absolute loss margin"); ax.set_yticks(range(5)); ax.grid(alpha=.15); ax.spines[["top","right"]].set_visible(False)
    axs[0].set_ylabel("largest non-inferior omission"); axs[1].legend(frameon=False); fig.suptitle("Post-hoc margin sensitivity",fontsize=20,weight="bold",color=NAVY)
    fig.text(.02,.01,"VERIFIED SENSITIVITY ANALYSIS · only the 0.10 margin was primary",fontsize=8.5,color=MUTED,weight="bold")
    save(fig,"06_PRIMARY_RESULTS","R06_margin_sensitivity","Margin sensitivity","Verified post-hoc sensitivity analysis","How the allowed margin changes the largest passing cutoff.","results/qft_certificate_gap/margin_summary_rows.csv")
margin_sensitivity()

def gap_matrix():
    fig,ax=newfig(11,6.4); titlebar(ax,"The certificate–endpoint gap",None)
    rows=[("Original certificate","0 layers","all 6 cells",RED), ("Held-out endpoint · omit 1","1 layer","passes 6 / 6",TEAL), ("Held-out endpoint · omit 2","2 layers","passes 2 / 6",PURPLE)]
    for i,(a,b,c,col) in enumerate(rows):
        y=.66-i*.20; rounded(ax,(.06,y-.075),.88,.15,"white",col,2); txt(ax,.09,y,a,13,INK,"bold"); txt(ax,.58,y,b,18,col,"bold",ha="center"); txt(ax,.90,y,c,13,col,"bold",ha="right")
    footer(ax,"Verified frozen certificate and endpoint comparison")
    save(fig,"06_PRIMARY_RESULTS","R07_certificate_gap_summary","Certificate–endpoint gap","Verified frozen result","Direct side-by-side primary conclusion.","results/qft_certificate_gap/certificate_gap_rows.csv")
gap_matrix()

# ---------------------------------------------------------------------------
# 07 — resources
# ---------------------------------------------------------------------------
def resource_bars():
    fig,axs=plt.subplots(1,3,figsize=(13,5.8)); fig.patch.set_facecolor(CREAM)
    labels=["Exact","Omit 1","Omit 2"]; vals=[[20,18,14],[52,48,40],[36,36,36]]; titles=["controlled phases","transpiled CX","depth"]
    for ax,v,t in zip(axs,vals,titles):
        bars=ax.bar(labels,v,color=[NAVY,TEAL,ORANGE]); ax.set_title(t,color=NAVY,weight="bold"); ax.spines[["top","right","left"]].set_visible(False); ax.grid(axis="y",alpha=.14); ax.tick_params(axis="x",rotation=20)
        for b,n in zip(bars,v): ax.text(b.get_x()+b.get_width()/2,n+.6,str(n),ha="center",weight="bold",color=INK)
    fig.suptitle("M = 32 QFT-only compiled resources",fontsize=21,weight="bold",color=NAVY)
    fig.text(.02,.01,"VERIFIED QFT-ONLY COUNTS · not total circuit cost · omit 2 passed only Model B",fontsize=8.5,color=MUTED,weight="bold")
    save(fig,"07_RESOURCE_SAVINGS","G01_M32_resource_bars","M=32 QFT-only resources","Verified compiled resource result","Exact, one-layer, and two-layer QFT resources.","results/qft_certificate_gap/configuration_rows.csv")
resource_bars()

generic_statement("07_RESOURCE_SAVINGS","G02_one_layer_savings","Conservative passing option",
                  "Omit one layer: −2 CP and −4 CX",
                  "This cutoff met the frozen 0.10 non-inferiority rule in all six model–M cells. Depth savings depend on M and are zero at M=16 and 32.",
                  TEAL,"Verified QFT-only resource + endpoint result","Universal tested one-layer resource card.","certificate_gap_rows.csv; configuration_rows.csv",number="6 / 6",dark=True)

generic_statement("07_RESOURCE_SAVINGS","G03_two_layer_savings","Largest passing tested option · finite Gaussian M=32",
                  "Omit two layers: −6 CP and −12 CX",
                  "This is the largest passing observed cutoff, and it had no QFT depth reduction after the tested transpilation. It did not pass in the hard-box model.",
                  ORANGE,"Verified QFT-only resource + endpoint result","Qualified maximum-saving card.","certificate_gap_rows.csv; configuration_rows.csv",number="0 depth",dark=True)

def gate_layers():
    fig,ax=newfig(13,6.3); titlebar(ax,"Which controlled-phase layers are removed?","M=32 uses q=5 Fourier qubits per register; d=2 registers.")
    ys=[.68,.56,.44,.32]; names=["separation 1","separation 2","separation 3","separation 4"]
    for i,(y,n) in enumerate(zip(ys,names)):
        txt(ax,.06,y,n,11,MUTED,"bold")
        for j in range(5-i-1): ax.add_patch(Circle((.34+j*.105,y),.025,facecolor=[NAVY,BLUE,CYAN,PURPLE][i],edgecolor="none"))
        if i>=2:
            rounded(ax,(.78,y-.035),.16,.07,PALE_ORANGE,ORANGE,1.5); txt(ax,.86,y,"omitted at 2 layers",8.5,ORANGE,"bold",ha="center")
    txt(ax,.52,.17,"Farthest, smallest-angle interactions are removed first",14,NAVY,"bold",ha="center")
    footer(ax,"Conceptual layer map; counts verified for M=32, d=2")
    save(fig,"07_RESOURCE_SAVINGS","G04_qft_layer_map","QFT layer map","Conceptual schematic with verified M=32 context","Shows which interaction distances truncation targets.","regev_research/circuits.py; configuration_rows.csv")
gate_layers()

def cost_acceptance():
    fig,ax=plt.subplots(figsize=(10,6)); fig.patch.set_facecolor(CREAM); ax.set_facecolor(CREAM)
    pts=[("Exact",52,6,NAVY),("Omit 1",48,6,TEAL),("Omit 2",40,2,PURPLE),("Omit 3",28,0,ORANGE),("Omit 4",12,0,RED)]
    for lab,cx,passes,col in pts:
        ax.scatter(cx,passes,s=220,color=col); ax.text(cx,passes+.25,lab,ha="center",weight="bold",color=col)
    ax.set_xlabel("M=32 QFT-only transpiled CX count"); ax.set_ylabel("model–M cells passing at that omission (of 6)"); ax.set_ylim(-.5,7); ax.grid(alpha=.16); ax.spines[["top","right"]].set_visible(False); ax.set_title("Resource reduction is useful only if recovery remains acceptable",color=NAVY,pad=16)
    fig.text(.02,.015,"VERIFIED COUNTS · x axis is M=32 QFT only; y axis aggregates all six endpoint cells",fontsize=8.5,color=MUTED,weight="bold")
    save(fig,"07_RESOURCE_SAVINGS","G05_cost_vs_acceptance","Cost vs accepted cells","Verified descriptive synthesis","Shows resource/endpoint tradeoff without implying speedup.","certificate_gap_rows.csv; configuration_rows.csv")
cost_acceptance()

# ---------------------------------------------------------------------------
# 08 — robustness / diagnostics
# ---------------------------------------------------------------------------
def loo_heatmap():
    rows=[r for r in LOO if int(r["omitted_layers"])==1]
    models=["A_uniform_hard_box","B_exact_finite_discrete_gaussian"]; ms=[8,16,32]; ns=[55,65,85,95,115,119,133,161]
    arr=np.zeros((6,8)); labs=[]
    for ri,(model,M) in enumerate((m,M) for m in models for M in ms):
        labs.append(f"{'A' if model.startswith('A') else 'B'} · M{M}")
        for ci,N in enumerate(ns):
            rr=next(r for r in rows if r["model"]==model and int(r["M"])==M and int(r["omitted_N"])==N)
            arr[ri,ci]=1 if rr["noninferior_at_0_10"]=="True" else 0
    fig,ax=plt.subplots(figsize=(12,5.5)); fig.patch.set_facecolor(CREAM); ax.imshow(arr,cmap=mpl.colors.ListedColormap([PALE_ORANGE,PALE_TEAL]),vmin=0,vmax=1,aspect="auto")
    for r in range(6):
        for c in range(8): ax.text(c,r,"pass" if arr[r,c] else "fail",ha="center",va="center",fontsize=8,weight="bold",color=TEAL if arr[r,c] else RED)
    ax.set_xticks(range(8),[f"omit N={n}" for n in ns],rotation=30,ha="right"); ax.set_yticks(range(6),labs); ax.set_title("Leave-one-modulus-out stability of the one-layer result",color=NAVY,pad=16)
    for s in ax.spines.values(): s.set_visible(False)
    fig.text(.02,.01,"VERIFIED SENSITIVITY ANALYSIS · each cell reruns the N-cluster decision after removing one modulus",fontsize=8.5,color=MUTED,weight="bold")
    save(fig,"08_ROBUSTNESS_AND_DIAGNOSTICS","D01_leave_one_N_out","Leave-one-N-out stability","Verified sensitivity analysis","One-layer decision under every leave-one-N-out dataset.","results/qft_certificate_gap/leave_one_N_out_rows.csv")
loo_heatmap()

def slack_plot():
    names=["omitted_gate_triangle","product_tensor_triangle","prepared_state_restriction","measurement_data_processing","sample_union_vs_hellinger","distribution_bound_vs_factor_event"]
    med=[]
    for n in names:
        vals=[]
        for r in SLACK:
            if r["proof_step"] != n or not r["slack_factor"].strip():
                continue
            v=float(r["slack_factor"])
            if math.isfinite(v):
                vals.append(v)
        med.append(np.median(vals))
    fig,ax=plt.subplots(figsize=(11,6)); fig.patch.set_facecolor(CREAM); ax.set_facecolor(CREAM)
    labels=["gate triangle","d-register tensor","prepared-state restriction","measurement processing","m-sample composition","factor event"]
    bars=ax.barh(labels,med,color=[ORANGE,PURPLE,BLUE,CYAN,GOLD,TEAL]); ax.set_xscale("log"); ax.set_xlabel("median bound / observed value (log scale)"); ax.set_title("Where conservatism enters the certificate",color=NAVY,pad=16); ax.axvline(1,color=NAVY,lw=1); ax.grid(axis="x",alpha=.15); ax.spines[["top","right","left"]].set_visible(False)
    for b,v in zip(bars,med): ax.text(v*1.04,b.get_y()+b.get_height()/2,f"{v:.2f}×",va="center",weight="bold",color=INK)
    fig.text(.02,.01,"VERIFIED PROOF-SLACK AUDIT · descriptive medians across finite configurations",fontsize=8.5,color=MUTED,weight="bold")
    save(fig,"08_ROBUSTNESS_AND_DIAGNOSTICS","D02_proof_slack","Certificate proof slack","Verified diagnostic analysis","Median looseness at each certificate step.","results/qft_certificate_gap/proof_slack_rows.csv")
slack_plot()

def tv_diagnostics():
    fig,axs=plt.subplots(1,2,figsize=(12,5.8),sharey=True); fig.patch.set_facecolor(CREAM)
    for ax,model,title in zip(axs,["A_uniform_hard_box","B_exact_finite_discrete_gaussian"],["A · hard box","B · finite Gaussian"]):
        for omit,col in zip([1,2],[TEAL,ORANGE]):
            vals=[]
            for M in [8,16,32]:
                rs=[float(r["distribution_tv"]) for r in CONFIG if r["model"]==model and int(r["M"])==M and int(r["omitted_layers"])==omit]
                vals.append(np.mean(rs) if rs else np.nan)
            ax.plot([8,16,32],vals,marker="o",lw=2.5,color=col,label=f"omit {omit}")
        ax.set_title(title,color=NAVY,weight="bold"); ax.set_xlabel("M"); ax.grid(alpha=.15); ax.spines[["top","right"]].set_visible(False)
    axs[0].set_ylabel("mean one-shot distribution TV across N"); axs[1].legend(frameon=False); fig.suptitle("Prepared-law change is model dependent",fontsize=20,weight="bold",color=NAVY)
    fig.text(.02,.01,"VERIFIED FINITE DIAGNOSTIC · descriptive only; primary endpoint is factor recovery",fontsize=8.5,color=MUTED,weight="bold")
    save(fig,"08_ROBUSTNESS_AND_DIAGNOSTICS","D03_distribution_tv","Finite distribution diagnostics","Verified finite diagnostic","TV change in the exact finite measured law.","results/qft_certificate_gap/configuration_rows.csv")
tv_diagnostics()

generic_statement("08_ROBUSTNESS_AND_DIAGNOSTICS","D04_implementation_correction","Verified implementation correction",
                  "The custom approximate inverse QFT had its gate order reversed",
                  "A previous full-cutoff test silently substituted a library QFT and masked the bug. The implementation was fixed before the frozen holdout, and every result was regenerated.",
                  RED,"Verified pre-holdout implementation correction","Transparent software-audit card.","QFT_CERTIFICATE_GAP_ADVERSARIAL_AUDIT.md; latex_short_paper/main.tex",dark=False)

generic_statement("08_ROBUSTNESS_AND_DIAGNOSTICS","D05_near_tight_gate_step","Adversarial proof audit",
                  "The first gate-level step can be almost tight",
                  "At M=128, q=7, cutoff=5: operator error 0.049082 versus phase-sum bound 0.049087 — a tightness ratio of 0.9998996. The important slack appears later.",
                  ORANGE,"Verified controlled adversarial example","Shows why the proof cannot be dismissed wholesale.","results/qft_certificate_gap/controlled_examples.json",number="99.99%",dark=True)

# ---------------------------------------------------------------------------
# 09 — limitations / claims
# ---------------------------------------------------------------------------
def scope_grid():
    fig,ax=newfig(12,7); titlebar(ax,"What was tested — and what was not",None)
    yes=["8 small held-out semiprimes","d=2 and m=7","M=8,16,32","hard-box exact finite law","finite-Gaussian exact law","current integer-LLL endpoint"]
    no=["cryptographic-size N","asymptotic Regev regime","hardware noise / full devices","total circuit runtime speedup","all base families or decoders","universal approximate-QFT theorem"]
    for x,title,col,items in [(.05,"TESTED",TEAL,yes),(.52,"NOT ESTABLISHED",RED,no)]:
        rounded(ax,(x,.14),.43,.65,"white",col,2); txt(ax,x+.04,.72,title,16,col,"bold")
        for i,it in enumerate(items): txt(ax,x+.06,.62-i*.075,("✓ " if col==TEAL else "— ")+it,11,INK,"bold")
    footer(ax,"Verified scope statement")
    save(fig,"09_LIMITATIONS_AND_CLAIMS","L01_scope_grid","Scope grid","Verified scope statement","Tested vs unestablished claims.","latex_short_paper/main.tex")
scope_grid()

generic_statement("09_LIMITATIONS_AND_CLAIMS","L02_no_speedup_claim","Important limitation",
                  "Gate savings do not yet equal hardware speedup",
                  "The resource counts cover only the QFT block after one tested transpilation. Modular arithmetic, state preparation, routing, error correction, and device noise are outside the measured claim.",
                  RED,"Verified claim limitation","Poster guardrail against end-to-end speedup language.","latex_short_paper/main.tex",dark=True)

generic_statement("09_LIMITATIONS_AND_CLAIMS","L03_model_B_limit","Model-B limitation",
                  "Finite Gaussian is closer to Regev — but it is not the full theorem regime",
                  "Model B uses a centered, truncated finite discrete-Gaussian amplitude with R=4. It tests a mechanism at small finite parameters; it does not validate asymptotic sampling guarantees.",
                  PURPLE,"Verified model limitation","Precise finite-Gaussian boundary.","latex_short_paper/main.tex",dark=False)

def three_claims():
    fig,ax=newfig(12,7); titlebar(ax,"Three claims, three evidence labels",None)
    cards=[("VERIFIED CORRECTION","QFT gate-order bug fixed before holdout",BLUE),
           ("VERIFIED EMPIRICAL RESULT","One omitted layer passed all six frozen cells",TEAL),
           ("UNVERIFIED GENERALIZATION","Full asymptotic Regev sampling may behave differently",ORANGE)]
    for i,(h,b,c) in enumerate(cards):
        y=.66-i*.20; rounded(ax,(.06,y-.075),.88,.15,"white",c,2); txt(ax,.09,y+.025,h,10,c,"bold"); txt(ax,.09,y-.035,b,13,INK,"bold")
    footer(ax,"Evidence-calibrated claim language")
    save(fig,"09_LIMITATIONS_AND_CLAIMS","L04_three_claims","Three evidence labels","Verified evidence taxonomy","Ready-to-use conclusion graphic.","latex_short_paper/main.tex")
three_claims()

generic_statement("09_LIMITATIONS_AND_CLAIMS","L05_why_it_matters","Why this matters",
                  "Certify the state and task you actually run",
                  "A safe all-input transform bound may spend precision protecting states and events the algorithm never uses. Fiber-aware, endpoint-aware certification could recover real resources without weakening the observed decoder target.",
                  CYAN,"Interpretive implication supported by mechanism + experiment","Closing significance card; framed as future direction.","QFT_CERTIFICATE_PROOF_AUDIT.md; certificate_gap_rows.csv",dark=True)

# ---------------------------------------------------------------------------
# 10 — decorative vector motifs (not data)
# ---------------------------------------------------------------------------
def lattice_motif():
    fig,ax=newfig(8,8,dark=True)
    for i in range(-7,8):
        for j in range(-7,8):
            x=.5+i*.06+j*.025; y=.5+j*.055
            if 0.04<x<.96 and .04<y<.96:
                d=math.hypot(i,j); col=TEAL if (i,j)==(2,-1) else (CYAN if d<5 else "#315276")
                ax.add_patch(Circle((x,y),.008 if d>0 else .018,facecolor=col,edgecolor="none",alpha=.95))
    arrow(ax,(.5,.5),(.645,.445),ORANGE,4); txt(ax,.66,.43,"useful relation",12,ORANGE,"bold")
    footer(ax,"Decorative mathematical motif · not data",True)
    save(fig,"10_DECORATIVE_VECTORS","V01_lattice_field","Lattice field motif","Decorative schematic; not data","Square poster background or accent.","Conceptual")
lattice_motif()

def fourier_motif():
    fig,ax=newfig(8,8,dark=True)
    for r,c,lw in zip(np.linspace(.08,.42,8),[CYAN,BLUE,PURPLE,ORANGE,TEAL,CYAN,BLUE,PURPLE],[3,2,4,2,3,2,2,3]):
        th=np.linspace(0,2*np.pi,500); rr=r*(1+.08*np.sin(5*th)); ax.plot(.5+rr*np.cos(th),.5+rr*np.sin(th),color=c,lw=lw,alpha=.8)
    ax.add_patch(Circle((.5,.5),.025,facecolor=ORANGE,edgecolor="white")); footer(ax,"Decorative Fourier motif · not data",True)
    save(fig,"10_DECORATIVE_VECTORS","V02_fourier_rings","Fourier rings motif","Decorative schematic; not data","Square visual accent.","Conceptual")
fourier_motif()

def fiber_motif():
    fig,ax=newfig(12,5,dark=True)
    for row,c in enumerate([CYAN,PURPLE,ORANGE,TEAL]):
        for j in range(4):
            p=(.08+j*.09,.74-row*.16); ax.add_patch(Circle(p,.018,facecolor=c,edgecolor="none")); arrow(ax,(p[0]+.02,p[1]),(.72,.50),c,1.2,connectionstyle=f"arc3,rad={(row-1.5)*.10}")
    ax.add_patch(Circle((.76,.50),.07,facecolor="none",edgecolor="white",lw=2)); arrow(ax,(.83,.50),(.94,.50),ORANGE,3); footer(ax,"Decorative fiber motif · not data",True)
    save(fig,"10_DECORATIVE_VECTORS","V03_fiber_streams","Fiber streams motif","Decorative schematic; not data","Wide visual divider.","Conceptual")
fiber_motif()


def write_manifest_and_contacts():
    # Add externally assembled repository figures and AI concepts without
    # altering their files or accompanying documentation.
    known={(r["folder"],r["id"]) for r in MANIFEST}
    for folder,evidence in [("11_EXISTING_REPO_FIGURES","Existing repository figure; inspect README evidence labels"),
                            ("12_DECORATIVE_AI_CONCEPTS","Decorative AI concept; NOT DATA")]:
        for p in sorted((OUT/folder).glob("*.png")):
            if (folder,p.stem) not in known:
                MANIFEST.append({"id":p.stem,"folder":folder,"title":p.stem.replace("_"," "),
                                 "evidence_level":evidence,"caption":"Pre-existing asset included for poster selection.",
                                 "source":str(p.relative_to(ROOT)),"files":p.name})
    fields=["id","folder","title","evidence_level","caption","source","files"]
    with (OUT/"ASSET_MANIFEST.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(MANIFEST)
    lines=["# Poster graphics asset manifest","",
           "Quantitative graphics are generated from the frozen `results/qft_certificate_gap/` files. ",
           "Conceptual and decorative assets are explicitly labeled. PNG is for slides/posters; SVG is editable vector artwork.",""]
    for r in MANIFEST:
        lines += [f"## {r['id']}","",f"- Folder: `{r['folder']}`",f"- Evidence: **{r['evidence_level']}**",f"- Caption: {r['caption']}",f"- Source: `{r['source']}`",""]
    (OUT/"ASSET_MANIFEST.md").write_text("\n".join(lines))

    # Build category sheets plus one all-assets sheet.  Use PNGs only.
    groups={}
    for p in OUT.glob("[0-9][0-9]_*/*.png"):
        if p.parent.name=="13_CONTACT_SHEETS": continue
        groups.setdefault(p.parent.name,[]).append(p)
    groups["ALL_ASSETS"]=[p for ps in groups.values() for p in ps]
    font=ImageFont.load_default()
    for name,paths in groups.items():
        paths=sorted(paths); cols=4; cell_w,cell_h=520,350; rows=math.ceil(len(paths)/cols)
        canvas=Image.new("RGB",(cols*cell_w,rows*cell_h),(255,253,247)); draw=ImageDraw.Draw(canvas)
        for i,p in enumerate(paths):
            try:
                im=Image.open(p).convert("RGB")
            except (OSError, ValueError):
                # Another packaging process may be writing a preview while
                # this generator runs; omit only that transient preview.
                continue
            im.thumbnail((cell_w-24,cell_h-55),Image.Resampling.LANCZOS)
            x=(i%cols)*cell_w+(cell_w-im.width)//2; y=(i//cols)*cell_h+8
            canvas.paste(im,(x,y)); draw.text(((i%cols)*cell_w+12,(i//cols)*cell_h+cell_h-38),p.stem,fill=(19,41,75),font=font)
        canvas.save(OUT/"13_CONTACT_SHEETS"/f"CONTACT_{name}.jpg",quality=88,optimize=True)


write_manifest_and_contacts()
print(f"Generated {len([r for r in MANIFEST if r['folder'] not in ('11_EXISTING_REPO_FIGURES','12_DECORATIVE_AI_CONCEPTS')])} code-native assets")
print(f"Manifest contains {len(MANIFEST)} total selectable PNG assets")
