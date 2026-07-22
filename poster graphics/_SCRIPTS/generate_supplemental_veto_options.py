#!/usr/bin/env python3
"""Generate compact poster-ready alternatives from frozen repository data."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Rectangle
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
POSTER = ROOT / "poster graphics"
OUT = POSTER / "14_SUPPLEMENTAL_VETO_OPTIONS"
DATA = POSTER / "_SOURCE_DATA"

NAVY = "#13294B"
ORANGE = "#FF5F05"
BLUE = "#0072B2"
CYAN = "#28A9C7"
PURPLE = "#7E57C2"
TEAL = "#009E73"
VERMILION = "#D55E00"
PLUM = "#6F4A8E"
WARM = "#F7F8FA"
SLATE = "#526273"
LIGHT_BLUE = "#DCECF7"
LIGHT_ORANGE = "#FFF0E8"

MANIFEST: list[dict[str, str]] = []


def setup() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 15,
            "axes.titleweight": "bold",
            "axes.titlesize": 23,
            "axes.labelsize": 17,
            "xtick.labelsize": 14,
            "ytick.labelsize": 14,
            "text.color": NAVY,
            "axes.labelcolor": NAVY,
            "axes.edgecolor": NAVY,
            "xtick.color": NAVY,
            "ytick.color": NAVY,
            "figure.facecolor": WARM,
            "axes.facecolor": WARM,
            "savefig.facecolor": WARM,
            "svg.fonttype": "none",
        }
    )


def export(fig, name: str, level: str, source: str, caption: str) -> None:
    fig.tight_layout(pad=1.6)
    for extension in ("png", "svg", "pdf"):
        path = OUT / f"{name}.{extension}"
        kwargs = {"bbox_inches": "tight"}
        if extension == "png":
            kwargs["dpi"] = 220
        fig.savefig(path, **kwargs)
    plt.close(fig)
    MANIFEST.append(
        {
            "asset": name,
            "evidence_level": level,
            "source": source,
            "caption": caption,
        }
    )


def rounded(ax, xy, width, height, color, edge=NAVY, radius=0.03, lw=2, alpha=1):
    patch = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle=f"round,pad=0.018,rounding_size={radius}",
        transform=ax.transAxes,
        facecolor=color,
        edgecolor=edge,
        linewidth=lw,
        alpha=alpha,
    )
    ax.add_patch(patch)
    return patch


def arrow(ax, start, end, color=ORANGE, lw=3):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            transform=ax.transAxes,
            arrowstyle="-|>",
            mutation_scale=20,
            linewidth=lw,
            color=color,
            zorder=8,
        )
    )


def number_tiles() -> None:
    fig, ax = plt.subplots(figsize=(14, 5.4))
    ax.axis("off")
    tiles = [
        ("0", "non-exact layers\ncertified", PLUM),
        ("6/6", "tested cells passed\nwith one layer omitted", TEAL),
        ("2", "Gaussian cells passed\nwith two layers omitted", PURPLE),
        ("12", "QFT-only transpiled\nCX gates saved, at most", ORANGE),
    ]
    for i, (big, label, color) in enumerate(tiles):
        x = 0.02 + i * 0.245
        rounded(ax, (x, 0.12), 0.215, 0.72, "white", edge=color, radius=0.04, lw=4)
        ax.text(x + 0.1075, 0.61, big, transform=ax.transAxes, ha="center", va="center",
                fontsize=49, weight="bold", color=color)
        ax.text(x + 0.1075, 0.32, label, transform=ax.transAxes, ha="center", va="center",
                fontsize=16, color=NAVY, linespacing=1.25)
    ax.set_title("The finite held-out result in four numbers", pad=14)
    export(fig, "S01_headline_four_number_tiles", "primary",
           "certificate_gap_rows.csv; configuration_rows.csv",
           "Original certificate: zero omitted layers. One layer passed all six tested cells; two passed in two Gaussian cells; maximum saving was 12 QFT-only CX gates.")


def threshold_ruler() -> None:
    fig, ax = plt.subplots(figsize=(13, 5.2))
    threshold = 4 * np.pi * 2 * 7 / 0.05
    ax.set_xscale("log", base=2)
    ax.set_xlim(6, 5000)
    ax.set_ylim(-0.7, 1.0)
    ax.hlines(0, 8, threshold, color=PLUM, linewidth=12, alpha=.25)
    ax.hlines(0, threshold, 5000, color=TEAL, linewidth=12, alpha=.25)
    label_heights = {8: .18, 16: .34, 32: .50}
    for value in (8, 16, 32):
        ax.scatter(value, 0, s=260, color=ORANGE, edgecolor=NAVY, linewidth=2, zorder=3)
        ax.text(value, label_heights[value], f"tested M={value}", ha="center", fontsize=15, weight="bold")
    ax.scatter(threshold, 0, s=320, marker="D", color=PLUM, edgecolor=NAVY, linewidth=2, zorder=3)
    ax.text(threshold, .3, f"certificate threshold\n{threshold:.1f}", ha="center", fontsize=16, weight="bold", color=PLUM)
    ax.text(150, -.42, "certificate cannot approve a non-exact cutoff", ha="center", color=PLUM, fontsize=17)
    ax.text(4100, -.42, "first layer may be certifiable", ha="center", color=TEAL, fontsize=16)
    ax.set_yticks([])
    ax.set_xticks([8,16,32,128,512,2048,4096], labels=["8","16","32","128","512","2048","4096"])
    ax.set_xlabel("Fourier modulus M (log₂ scale)")
    ax.set_title("What the worst-case certificate predicted", pad=18)
    ax.spines[["left","right","top"]].set_visible(False)
    export(fig, "S02_certificate_threshold_log_ruler", "proved",
           "QFT_CERTIFICATE_PROOF_AUDIT.md; configuration.json",
           "For d=2, m=7 and Delta=.05, the first non-exact certificate threshold is M≈3518.6; tested M values are far below it. This is a certificate limitation, not physical necessity.")


def certification_heatmap() -> None:
    df = pd.read_csv(DATA / "certificate_gap_rows.csv")
    models = ["A_uniform_hard_box", "B_exact_finite_discrete_gaussian"]
    Ms = [8,16,32]
    values=np.zeros((2,3),int)
    for i,model in enumerate(models):
        for j,M in enumerate(Ms):
            values[i,j]=int(df[(df.model==model)&(df.M==M)].empirically_noninferior_layers.iloc[0])
    fig,ax=plt.subplots(figsize=(9.5,5.5))
    cmap=plt.matplotlib.colors.ListedColormap(["#E7E9ED", "#A7E2D4", "#C8B5E8"])
    ax.imshow(values,vmin=0,vmax=2,cmap=cmap,aspect="auto")
    for i in range(2):
        for j in range(3):
            ax.text(j,i,f"0 → {values[i,j]}",ha="center",va="center",fontsize=28,weight="bold",color=NAVY)
            ax.text(j,i+.28,"certified → held-out",ha="center",va="center",fontsize=11,color=SLATE)
    ax.set_xticks(range(3),[f"M={m}" for m in Ms])
    ax.set_yticks(range(2),["A · hard box", "B · finite Gaussian"])
    ax.set_title("Certified layers versus empirically non-inferior layers")
    ax.set_xlabel("Frozen 0.10 non-inferiority margin; every cell used eight held-out N values")
    for spine in ax.spines.values(): spine.set_visible(False)
    export(fig,"S03_main_six_cell_certificate_gap","primary",
           "certificate_gap_rows.csv",
           "Each cell shows original certified omitted layers (zero) and largest omission meeting the frozen held-out rule.")


def forest_plot() -> None:
    df=pd.read_csv(DATA/"paired_cluster_rows.csv")
    chosen=df[df.empirically_noninferior.astype(str)=="True"].sort_values("omitted_layers").groupby(["M","model"],as_index=False).tail(1)
    chosen=chosen.sort_values(["M","model"]).reset_index(drop=True)
    labels=[]
    for _,r in chosen.iterrows():
        model="A" if str(r.model).startswith("A_") else "B"
        labels.append(f"M={int(r.M)}, {model}, omit {int(r.omitted_layers)}")
    y=np.arange(len(chosen))[::-1]
    means=chosen.factor_mean_difference.to_numpy()
    lows=chosen.factor_cluster_ci95_low.to_numpy()
    highs=chosen.factor_cluster_ci95_high.to_numpy()
    colors=[CYAN if ", A," in lab else PURPLE for lab in labels]
    fig,ax=plt.subplots(figsize=(11,6.5))
    for yi,mu,lo,hi,c in zip(y,means,lows,highs,colors):
        ax.plot([lo,hi],[yi,yi],color=c,lw=5,solid_capstyle="round")
        ax.scatter(mu,yi,s=180,color=c,edgecolor=NAVY,lw=1.5,zorder=3)
    ax.axvline(-.10,color=VERMILION,lw=3,ls="--",label="frozen −0.10 margin")
    ax.axvline(0,color=NAVY,lw=1.5)
    ax.set_yticks(y,labels)
    ax.set_xlim(-.115,.02)
    ax.set_xlabel("Approximate − exact factor-recovery probability")
    ax.set_title("Selected passing cutoffs remained above the frozen loss margin")
    ax.legend(loc="upper left",frameon=False)
    ax.grid(axis="x",alpha=.2)
    ax.spines[["right","top"]].set_visible(False)
    export(fig,"S04_primary_cluster_forest_plot","primary",
           "paired_cluster_rows.csv",
           "Mean paired factor-recovery differences and 95% whole-N cluster-bootstrap intervals for the largest passing omission in each cell.")


def resources() -> None:
    labels=["Exact","Omit 1","Omit 2"]
    data={"Logical controlled phases":[20,18,14],"Transpiled CX (QFT only)":[52,48,40],"QFT-only depth":[36,36,36]}
    fig,axes=plt.subplots(1,3,figsize=(15,5.2))
    colors=[BLUE,CYAN,ORANGE]
    for ax,(title,vals) in zip(axes,data.items()):
        bars=ax.bar(labels,vals,color=colors,edgecolor=NAVY,lw=1.5)
        for bar,val in zip(bars,vals): ax.text(bar.get_x()+bar.get_width()/2,val+max(vals)*.035,str(val),ha="center",weight="bold",fontsize=18)
        ax.set_title(title,fontsize=19)
        ax.set_ylim(0,max(vals)*1.22)
        ax.spines[["right","top","left"]].set_visible(False)
        ax.set_yticks([])
    fig.suptitle(
        "At M=32, the passing one- and two-layer cutoffs remove gates—not QFT depth",
        fontsize=24,
        weight="bold",
        color=NAVY,
    )
    fig.text(.5,.01,"Fixed rz/sx/x/cx transpilation · excludes modular arithmetic · not an end-to-end hardware speedup",ha="center",fontsize=14,color=VERMILION)
    export(fig,"S05_M32_qft_only_resources","primary resource accounting",
           "configuration_rows.csv",
           "At M=32,d=2: exact/omit-one/omit-two use 20/18/14 controlled phases and 52/48/40 QFT-only CX gates; compiled depth remains 36.")


def proof_slack() -> None:
    labels=["Gate\ntriangle","Product\ntensor","Prepared\nstate","Measured\nlaw","Sample\ncomposition","Factor\nevent"]
    vals=[1.18,1.96,2.09,6.80,1.38,3.92]
    colors=[BLUE,BLUE,PURPLE,ORANGE,PURPLE,TEAL]
    fig,ax=plt.subplots(figsize=(12,5.8))
    y=np.arange(len(vals))[::-1]
    ax.hlines(y,1,vals,color=colors,lw=6,alpha=.75)
    ax.scatter(vals,y,s=230,color=colors,edgecolor=NAVY,lw=1.5,zorder=3)
    for x,yi in zip(vals,y): ax.text(x+.12,yi,f"{x:.2f}×",va="center",fontsize=17,weight="bold")
    ax.axvline(1,color=NAVY,lw=2)
    ax.set_yticks(y,labels)
    ax.set_xlim(.8,7.6)
    ax.set_xlabel("Median finite bound / observed quantity")
    ax.set_title("Most certificate slack appears after the gate-level bound")
    ax.grid(axis="x",alpha=.2)
    ax.spines[["right","top"]].set_visible(False)
    export(fig,"S06_proof_slack_lollipop","mechanism audit",
           "proof_slack_rows.csv; QFT_CERTIFICATE_TIGHTNESS.md",
           "Median finite slack by proof step. Large state-to-measurement slack motivates the fiber-cancellation analysis.")


def state_models() -> None:
    M=32
    z=np.arange(-M//2,M//2)
    hard=np.ones(M)
    gauss=np.exp(-np.pi*z*z/16)
    fig,axes=plt.subplots(1,2,figsize=(12,4.8),sharey=True)
    axes[0].bar(z,hard,color=CYAN,edgecolor=NAVY,lw=.6)
    axes[1].plot(z,gauss,color=PURPLE,lw=4)
    axes[1].fill_between(z,gauss,color=PURPLE,alpha=.22)
    axes[0].set_title("A · uniform hard box", fontsize=20, pad=10)
    axes[1].set_title("B · finite Gaussian, R=4", fontsize=20, pad=10)
    for ax in axes:
        ax.set_xlabel("Centered exponent coordinate")
        ax.set_ylim(0,1.12); ax.grid(axis="y",alpha=.2); ax.spines[["right","top"]].set_visible(False)
    axes[0].set_ylabel("Amplitude weight")
    fig.suptitle(
        "Two exact finite state models test whether the result is surrogate-specific",
        fontsize=22,
        weight="bold",
    )
    fig.text(.5,.01,"Model B is closer to Regev's state, but neither panel establishes the full asymptotic algorithm",ha="center",color=VERMILION,fontsize=13)
    export(fig,"S07_hardbox_vs_finite_gaussian","illustrative model definition",
           "regev_research/redteam.py; configuration.json",
           "The hard box uses constant amplitudes; the finite Gaussian uses exp(-pi z^2/R^2) with R=4.")


def n15_cancellation() -> None:
    import sys
    sys.path.insert(0,str(ROOT))
    from regev_research.qft_noise import fiber_fourier_distribution
    exact=fiber_fourier_distribution(15,(4,1),4,cutoff=1)
    trunc=fiber_fourier_distribution(15,(4,1),4,cutoff=0)
    diff=np.abs(exact-trunc)
    fig,axes=plt.subplots(1,3,figsize=(13,4.4))
    titles=["Exact QFT","Truncated QFT","Absolute difference"]
    arrays=[exact,trunc,diff]
    cmaps=["Blues","Oranges","Blues"]
    for ax,title,array,cmap in zip(axes,titles,arrays,cmaps):
        # Use a fixed near-zero scale for the difference panel so numerical
        # roundoff is rendered as white rather than as a visually maximal
        # dark cell.
        vmax = .5 if title != "Absolute difference" else 1e-12
        ax.imshow(array,cmap=cmap,vmin=0,vmax=vmax)
        ax.set_title(title); ax.set_xlabel("k₂"); ax.set_ylabel("k₁")
        for (i,j),v in np.ndenumerate(array):
            if v>.001: ax.text(j,i,f"{v:.1f}",ha="center",va="center",weight="bold",color="white" if v>.25 else NAVY)
        if title == "Absolute difference":
            ax.text(
                1.5,
                1.5,
                "numerical zero",
                ha="center",
                va="center",
                fontsize=18,
                weight="bold",
                color=NAVY,
            )
    fig.suptitle("A rejected cutoff can have the same measured law",fontsize=24,weight="bold")
    fig.text(.5,-.045,"Deliberately favorable N=15 example · numerical TV = 5.9×10⁻³⁵ · logical counterexample, not broad factoring evidence",ha="center",fontsize=13,color=VERMILION)
    export(fig,"S08_N15_identical_measurement_law","controlled counterexample",
           "controlled_examples.json; fiber_fourier_distribution",
           "For N=15,bases=(4,1),M=4,t=0, exact and truncated measured laws coincide numerically although the all-state certificate rejects.")


def heldout_mosaic() -> None:
    values=[55,65,85,95,115,119,133,161]
    fig,ax=plt.subplots(figsize=(13,5))
    ax.axis("off")
    for i,value in enumerate(values):
        x=.14+(i%4)*.24; y=.67-(i//4)*.42
        circle=Circle((x,y),.085,transform=ax.transAxes,facecolor="white",edgecolor=TEAL,lw=4)
        ax.add_patch(circle)
        ax.text(x,y,str(value),transform=ax.transAxes,ha="center",va="center",fontsize=25,weight="bold")
    ax.text(.5,.94,"Eight frozen semiprimes are the generalization units",transform=ax.transAxes,ha="center",fontsize=25,weight="bold")
    ax.text(.5,.05,"64 coupled replicates estimate each N-specific probability; they do not create more independent moduli",transform=ax.transAxes,ha="center",fontsize=15,color=VERMILION)
    export(fig,"S09_eight_heldout_moduli","primary design",
           "configuration.json; QFT_CERTIFICATE_GAP_PROTOCOL.md",
           "Held-out N values: 55,65,85,95,115,119,133,161. No modulus was excluded.")


def pipeline() -> None:
    fig,ax=plt.subplots(figsize=(16,5.2)); ax.axis("off")
    steps=[
        ("stored roots","bᵢ",PURPLE), ("squared bases","aᵢ=bᵢ² mod N",CYAN),
        ("modular fibers","hₐ(x)",BLUE),("product QFT","d registers",ORANGE),
        ("samples","m rows",TEAL),("augmented\nlattice","exact integers",NAVY),
        ("LLL + verify","z ∈ L?",PLUM),("stored-root\ntest","L₀ or useful?",PURPLE),
        ("gcd","factor pair",ORANGE),
    ]
    width=.082
    for i,(top,bottom,color) in enumerate(steps):
        x=.015+i*.109
        rounded(ax,(x,.28),width,.42,"white",edge=color,radius=.025,lw=3)
        ax.text(x+width/2,.57,top,transform=ax.transAxes,ha="center",va="center",fontsize=12.5,weight="bold",color=color,linespacing=1.0)
        ax.text(x+width/2,.40,bottom,transform=ax.transAxes,ha="center",va="center",fontsize=12)
        if i<len(steps)-1:
            arrow(ax,(x+width+.002,.49),(x+.109-.006,.49),color=ORANGE,lw=2)
    ax.text(.5,.88,"The implemented Regev-style mathematical pipeline",transform=ax.transAxes,ha="center",fontsize=26,weight="bold")
    ax.text(.29,.16,"quantum model / exact finite simulation",transform=ax.transAxes,ha="center",fontsize=14,color=BLUE)
    ax.text(.75,.16,"classical exact-integer post-processing",transform=ax.transAxes,ha="center",fontsize=14,color=NAVY)
    export(fig,"S10_complete_sample_to_factor_pipeline","illustrative implementation map",
           "regev_research/lattice.py; QFT_CERTIFICATE_GAP_PROTOCOL.md",
           "Stored roots remain paired to squared circuit bases through sampling, augmented-lattice LLL, L/L0 classification and gcd extraction.")


def claim_zones() -> None:
    fig,ax=plt.subplots(figsize=(13,5.5)); ax.axis("off")
    zones=[
        ("PROVED", "The stated worst-case\ncertificate approves no\nnon-exact tested cutoff", PLUM),
        ("OBSERVED", "Limited truncation met\nthe frozen rule in this\neight-N finite holdout", TEAL),
        ("NOT ESTABLISHED", "Full Regev-regime sufficiency,\nhardware speedup, and\nuniversal safety", VERMILION),
    ]
    for i,(head,body,color) in enumerate(zones):
        x=.03+i*.325
        rounded(ax,(x,.18),.29,.62,"white",edge=color,radius=.04,lw=4)
        ax.text(x+.145,.64,head,transform=ax.transAxes,ha="center",fontsize=20,weight="bold",color=color)
        ax.text(x+.145,.40,body,transform=ax.transAxes,ha="center",va="center",fontsize=13.5,linespacing=1.35)
    ax.set_title("Keep the three claim levels separate",pad=16)
    export(fig,"S11_three_claim_zones","claim boundary",
           "QFT_CERTIFICATE_GAP_REPORT.md",
           "Separates the proved certificate limitation, the finite empirical result, and unverified general hypotheses.")


def shor_vs_regev() -> None:
    fig,ax=plt.subplots(figsize=(14,6)); ax.axis("off")
    rounded(ax,(.03,.16),.43,.68,"#EAF4FB",edge=BLUE,radius=.04,lw=4)
    rounded(ax,(.54,.16),.43,.68,"#F0EAF8",edge=PURPLE,radius=.04,lw=4)
    ax.text(.245,.73,"SHOR",transform=ax.transAxes,ha="center",fontsize=29,weight="bold",color=BLUE)
    ax.text(.755,.73,"REGEV",transform=ax.transAxes,ha="center",fontsize=29,weight="bold",color=PURPLE)
    ax.text(.245,.54,"one-dimensional phase / period",transform=ax.transAxes,ha="center",fontsize=17)
    ax.text(.245,.42,"continued fractions → verify order → gcd",transform=ax.transAxes,ha="center",fontsize=16)
    ax.text(.245,.29,"standard order-finding architecture",transform=ax.transAxes,ha="center",fontsize=14,color=SLATE)
    ax.text(.755,.54,"multidimensional Fourier samples",transform=ax.transAxes,ha="center",fontsize=17)
    ax.text(.755,.42,"augmented lattice → LLL → relation → gcd",transform=ax.transAxes,ha="center",fontsize=16)
    ax.text(.755,.29,"tested endpoint uses classical lattice reduction",transform=ax.transAxes,ha="center",fontsize=14,color=SLATE)
    ax.plot([.5,.5],[.23,.76],transform=ax.transAxes,color=ORANGE,lw=3,alpha=.8)
    ax.text(.5,.91,"Shor and this Regev-style implementation",transform=ax.transAxes,ha="center",fontsize=25,weight="bold")
    ax.text(.5,.06,"Descriptive comparison only · not an end-to-end speed or hardware claim",transform=ax.transAxes,ha="center",fontsize=14,color=VERMILION)
    export(fig,"S12_beginner_shor_vs_regev","background",
           "Shor 1994/1997; Regev 2025; shor_to_regev_study",
           "Shor uses one-dimensional period recovery; the tested Regev-style route uses multidimensional samples and lattice reduction.")


def qft_layers() -> None:
    q=5
    fig,axes=plt.subplots(1,3,figsize=(15,5.4))
    cutoffs=[4,3,2]; names=["Exact","Omit 1 layer","Omit 2 layers"]
    for ax,cutoff,name in zip(axes,cutoffs,names):
        ax.set_xlim(-.5,q-.5); ax.set_ylim(-.5,q-.5); ax.invert_yaxis(); ax.set_aspect("equal")
        for source in range(q):
            for target in range(source+1,q):
                separation=target-source
                kept=separation<=cutoff
                face=LIGHT_BLUE if kept else LIGHT_ORANGE
                edge=BLUE if kept else ORANGE
                ax.add_patch(
                    Rectangle(
                        (target-.39,source-.39),
                        .78,
                        .78,
                        facecolor=face,
                        edgecolor=edge,
                        linewidth=2.2,
                    )
                )
                ax.text(
                    target,
                    source,
                    "✓" if kept else "×",
                    ha="center",
                    va="center",
                    fontsize=16,
                    weight="bold",
                    color=edge,
                )
        kept=sum(q-r for r in range(1,q) if r<=cutoff)
        ax.set_title(f"{name}\n{2*kept} CP across d=2",fontsize=18)
        ax.set_xticks(range(q),[f"q{i}" for i in range(q)])
        ax.set_yticks(range(q),[f"q{i}" for i in range(q)])
        ax.set_xlabel("target qubit")
        if ax is axes[0]: ax.set_ylabel("source qubit")
        ax.grid(color="#D8DEE8",linewidth=.8,zorder=0)
        for spine in ax.spines.values(): spine.set_visible(False)
    fig.suptitle("Distance truncation removes the longest-range, smallest-angle interactions",fontsize=23,weight="bold")
    fig.text(.5,-.055,"Blue = retained controlled phase · orange × = omitted controlled phase",ha="center",fontsize=13,color=SLATE)
    export(fig,"S13_qft_phase_layer_cutaway","illustrative resource mechanism",
           "qft_gate_counts; configuration_rows.csv",
           "For M=32,q=5,d=2, exact/omit-one/omit-two use 20/18/14 logical controlled phases.")


def scope_fence() -> None:
    fig,ax=plt.subplots(figsize=(13,6)); ax.axis("off")
    rounded(ax,(.04,.13),.42,.72,"#E8F7F2",edge=TEAL,radius=.04,lw=4)
    rounded(ax,(.54,.13),.42,.72,"#FFF1EB",edge=VERMILION,radius=.04,lw=4)
    ax.text(.25,.75,"INSIDE THE EVIDENCE",transform=ax.transAxes,ha="center",fontsize=21,weight="bold",color=TEAL)
    ax.text(.75,.75,"OUTSIDE THE EVIDENCE",transform=ax.transAxes,ha="center",fontsize=21,weight="bold",color=VERMILION)
    inside=["8 small held-out semiprimes","d=2 and M≤32","hard-box + finite Gaussian","m=7, 64 coupled replicates","current exact-integer LLL endpoint"]
    outside=["cryptographic-scale N","calibrated hardware execution","full-circuit runtime speedup","all Regev parameter regimes","every possible postprocessor"]
    for i,item in enumerate(inside): ax.text(.09,.63-i*.10,"✓  "+item,transform=ax.transAxes,fontsize=16,va="center")
    for i,item in enumerate(outside): ax.text(.59,.63-i*.10,"×  "+item,transform=ax.transAxes,fontsize=16,va="center")
    ax.set_title("Exact limitation of the result",pad=16)
    export(fig,"S14_scope_fence","claim boundary",
           "QFT_CERTIFICATE_GAP_REPORT.md; configuration.json",
           "The finding is finite, model-specific, and decoder-specific; it does not establish hardware or asymptotic claims.")


def root_provenance() -> None:
    fig,ax=plt.subplots(figsize=(13,5.2)); ax.axis("off")
    blocks=[("selected root","bᵢ",PURPLE),("square once","aᵢ=bᵢ² mod N",ORANGE),("circuit uses","aᵢ",CYAN),("factor test retains","the same bᵢ",TEAL)]
    for i,(head,body,color) in enumerate(blocks):
        x=.04+i*.245; rounded(ax,(x,.26),.20,.48,"white",edge=color,radius=.04,lw=4)
        ax.text(x+.10,.60,head,transform=ax.transAxes,ha="center",fontsize=15,weight="bold",color=color)
        ax.text(x+.10,.42,body,transform=ax.transAxes,ha="center",fontsize=19,weight="bold")
        if i<3: arrow(ax,(x+.203,.50),(x+.245-.007,.50),color=ORANGE,lw=3)
    ax.text(.5,.88,"Root provenance is permanent metadata",transform=ax.transAxes,ha="center",fontsize=26,weight="bold")
    ax.text(.5,.10,"Never guess a modular square root later; classification uses the root that generated each circuit base",transform=ax.transAxes,ha="center",fontsize=15,color=VERMILION)
    export(fig,"S15_root_provenance_metadata","verified implementation correction",
           "regev_research/core.py; ROOT_PROVENANCE_RED_TEAM.md",
           "Each squared circuit base permanently retains its chosen generating root for L0 classification and factor extraction.")


def write_manifest() -> None:
    path=OUT/"SUPPLEMENTAL_MANIFEST.csv"
    with path.open("w",newline="",encoding="utf-8") as handle:
        writer=csv.DictWriter(handle,fieldnames=["asset","evidence_level","source","caption"])
        writer.writeheader(); writer.writerows(MANIFEST)


def main() -> None:
    OUT.mkdir(parents=True,exist_ok=True); setup()
    for func in [number_tiles,threshold_ruler,certification_heatmap,forest_plot,resources,
                 proof_slack,state_models,n15_cancellation,heldout_mosaic,pipeline,
                 claim_zones,shor_vs_regev,qft_layers,scope_fence,root_provenance]:
        func()
    write_manifest()
    print(f"Generated {len(MANIFEST)} supplemental poster graphics in PNG, SVG, and PDF.")


if __name__ == "__main__":
    main()
