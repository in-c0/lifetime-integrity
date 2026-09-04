#!/usr/bin/env python3
"""Regenerate every paper figure from the sealed confirmatory manifests.

No value is hand-copied. Run from the repository root:
    PYTHONPATH=src python paper/make_figures.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from lifetime_integrity.seeds import CONFIRMATORY_SEEDS

ROOT = Path("results/confirmatory/9954ab69cd4d")
OUT = Path("paper/figures")
HORIZONS = (8, 16, 32, 64, 128)
REPLICATES = 10_000

plt.rcParams.update({
    "figure.dpi": 160, "savefig.dpi": 300, "font.size": 9,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.5,
    "legend.frameon": False, "figure.constrained_layout.use": True,
})

# Cheap (zero-read) policies vs paid ones — the cost asymmetry is the result.
PAID = {"evidence-reconstruction", "provenance-regrounding", "contradiction-regrounding", "periodic-reset"}
COLORS = {
    "confidence-decay": "#0072B2", "periodic-reset": "#009E73",
    "evidence-reconstruction": "#D55E00", "provenance-regrounding": "#CC79A7",
    "last-write-wins": "#555555", "hybrid-symbolic-latent": "#56B4E9",
    "contradiction-regrounding": "#E69F00", "lossy-latent": "#999999",
    "unconstrained-accumulator": "#000000",
}


def cell(exp, seed, epochs):
    d = ROOT / exp / f"seed-{seed}" / f"epochs-{epochs}"
    return [json.loads(p.read_text()) for p in sorted(d.glob("*.json")) if p.name != "validation.json"]


def validity(exp, seed, epochs):
    return json.loads((ROOT / exp / f"seed-{seed}" / f"epochs-{epochs}" / "validation.json").read_text())


def valid_seeds(exp, epochs):
    return [s for s in CONFIRMATORY_SEEDS if validity(exp, s, epochs)["structurally_valid"]]


def boot_ci(vals, key):
    rng = np.random.default_rng(int.from_bytes(hashlib.sha256(key.encode()).digest()[:4], "big"))
    x = np.asarray(vals, dtype=float)
    m = x[rng.integers(0, len(x), size=(REPLICATES, len(x)))].mean(axis=1)
    return float(x.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"{name}.{ext}", bbox_inches="tight")
    plt.close(fig)
    print(f"  {name}.pdf / .png")


# ---------------------------------------------------------------- Figure 1
def fig1_concept():
    fig, ax = plt.subplots(figsize=(7.2, 3.1))
    ax.set_xlim(0, 100); ax.set_ylim(0, 42); ax.axis("off"); ax.grid(False)

    def box(x, y, w, h, label, fc, ec="#333333", fs=8):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.6",
                                    fc=fc, ec=ec, lw=0.9))
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=fs)

    def arrow(x1, y1, x2, y2, style="-|>", color="#333333", ls="-"):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                                     mutation_scale=9, lw=0.9, color=color, ls=ls))

    ax.text(1, 39.5, "hidden canonical world  (audit-only)", fontsize=8.5,
            style="italic", color="#8B0000")
    ax.add_patch(FancyBboxPatch((0.5, 27.5), 99, 10.5, boxstyle="round,pad=0.3",
                                fc="#FDF3F3", ec="#8B0000", lw=0.8, ls=(0, (4, 2))))
    for i, (x, t) in enumerate([(5, "slot values"), (26, "world change"),
                                (48, "which source lied"), (73, "culprit belief")]):
        box(x, 29.5, 18, 6, t, "#FBE9E9", "#8B0000", 7.5)

    ax.text(1, 24.0, "mechanism-visible stream", fontsize=8.5, style="italic", color="#00457C")
    for x, t in [(3, "assert\n(source, tier)"), (21, "contradiction"),
                 (39, "misinformation\n+ repetition"), (58, "inactivity\ngap"),
                 (75, "context\nshift")]:
        box(x, 13.5, 16, 8, t, "#EAF2FA", "#00457C", 7.5)
    for x in (19, 37, 56, 74):
        arrow(x, 17.5, x + 2, 17.5)

    box(30, 2.0, 22, 7, "maintenance policy\n(metered evidence reads)", "#EAF7EF", "#006B3C", 8)
    box(60, 2.0, 20, 7, "probe\n(never evidence)", "#FFF6E5", "#8A6100", 8)
    arrow(52, 5.5, 60, 5.5)
    arrow(41, 13.5, 41, 9.0)
    arrow(70, 13.5, 70, 9.0)
    arrow(70, 29.5, 70, 21.5, color="#8B0000", ls=(0, (3, 2)))
    ax.text(71.5, 25.0, "scored against,\nnever shown", fontsize=6.8, color="#8B0000", va="center")

    box(84, 2.0, 15, 7, "integrity\nmetrics", "#F0EAF7", "#4B0082", 8)
    arrow(80, 5.5, 84, 5.5)
    ax.text(0.5, 0.2, "G3: an answer can be canonical yet supported by nothing the system was ever told.",
            fontsize=7.4, color="#333333")
    save(fig, "fig1_concept")


# ---------------------------------------------------------------- Figure 2
def fig2_horizon():
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    arms = sorted(COLORS)
    for a in arms:
        means, los, his = [], [], []
        for E in HORIZONS:
            vals = [{r["arm"]: r["metrics"]["integrity_violation_rate"]
                     for r in cell("EXP-A001", s, E)}[a] for s in valid_seeds("EXP-A001", E)]
            m, lo, hi = boot_ci(vals, f"fig2/{a}/{E}")
            means.append(m); los.append(lo); his.append(hi)
        ls = "--" if a in PAID else "-"
        ax.plot(HORIZONS, means, ls, marker="o", ms=3.4, lw=1.5,
                color=COLORS[a], label=a)
        ax.fill_between(HORIZONS, los, his, color=COLORS[a], alpha=0.12, lw=0)
    ax.set_xscale("log", base=2); ax.set_xticks(HORIZONS)
    ax.set_xticklabels([str(e) for e in HORIZONS])
    ax.set_xlabel("lifetime length (epochs)")
    ax.set_ylabel("integrity violation rate")
    ax.set_title("Integrity degrades with lifetime; policies stay tightly bunched\n"
                 "and their order is unstable (quantified in Fig. 3)\n"
                 "dashed = spends evidence reads; bands = paired-seed bootstrap 95% CI",
                 fontsize=8.2, loc="left")
    ax.legend(fontsize=6.8, ncol=2, loc="upper left")
    save(fig, "fig2_integrity_vs_horizon")


# ---------------------------------------------------------------- Figure 3
def fig3_rank_instability():
    from run_development import _rank
    arms = sorted(COLORS)
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.6),
                             gridspec_kw={"width_ratios": [1.25, 1]})
    ax = axes[0]
    for s in CONFIRMATORY_SEEDS:
        r8 = _rank({r["arm"]: r["metrics"]["integrity_violation_rate"]
                    for r in cell("EXP-A001", s, 8)}, lower_is_better=True)
        r128 = _rank({r["arm"]: r["metrics"]["integrity_violation_rate"]
                      for r in cell("EXP-A001", s, 128)}, lower_is_better=True)
        for a in arms:
            ax.plot([0, 1], [r8[a], r128[a]], "-", color=COLORS[a], alpha=0.35, lw=0.9)
            ax.scatter([0, 1], [r8[a], r128[a]], s=7, color=COLORS[a], alpha=0.6, zorder=3)
    ax.set_xlim(-0.18, 1.18); ax.set_xticks([0, 1])
    ax.set_xticklabels(["rank at E8", "rank at E128"])
    ax.invert_yaxis(); ax.set_ylabel("rank by integrity violation (1 = best)")
    ax.set_title("Every seed, every mechanism", fontsize=8.5, loc="left")
    ax.grid(axis="x", alpha=0)

    a2 = axes[1]
    an = json.loads((ROOT / "analysis-audited.json").read_text())
    rhos = [d["rho"] for d in an["P1_A001_H2"]["per_seed"] if d["rho"] is not None]
    a2.scatter(rhos, range(len(rhos)), s=22, color="#0072B2", zorder=3)
    m, lo, hi = an["P1_A001_H2"]["mean"], an["P1_A001_H2"]["ci_low"], an["P1_A001_H2"]["ci_high"]
    a2.axvline(m, color="#0072B2", lw=1.4)
    a2.axvspan(lo, hi, color="#0072B2", alpha=0.15, lw=0)
    a2.axvline(0.6, color="#8B0000", ls="--", lw=1.2)
    a2.text(0.605, len(rhos) - 0.6, "frozen threshold 0.6", fontsize=7, color="#8B0000")
    a2.set_xlim(0, 1.02); a2.set_yticks([])
    a2.set_xlabel(r"per-seed Spearman $\rho$ (E8 vs E128)")
    a2.set_title(rf"mean $\rho$ = {m:.4f}   95% CI [{lo:.3f}, {hi:.3f}]"
                 f"\nall {len(rhos)} seeds below 0.6", fontsize=8.5, loc="left")
    save(fig, "fig3_rank_instability")


# ---------------------------------------------------------------- Figure 4
def fig4_frontier():
    """Cost/integrity frontier.

    Only Pareto members are annotated in-plot; the rest are keyed by the shared
    legend. Annotating all nine collides badly because reads cluster at three
    values (0, ~4e3, ~2.4e5).
    """
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.3))
    handles = None
    for ax, E in zip(axes, (64, 128)):
        seeds = valid_seeds("EXP-A001", E)
        pts = {}
        for a in sorted(COLORS):
            iv = np.mean([{r["arm"]: r["metrics"]["integrity_violation_rate"]
                           for r in cell("EXP-A001", s, E)}[a] for s in seeds])
            rd = np.mean([{r["arm"]: r["budget_actual"]["evidence_reads"]
                           for r in cell("EXP-A001", s, E)}[a] for s in seeds])
            pts[a] = (max(rd, 0.0), iv)
        front = [a for a in pts if not any(
            (pts[b][1] <= pts[a][1] and pts[b][0] <= pts[a][0]) and
            (pts[b][1] < pts[a][1] or pts[b][0] < pts[a][0]) for b in pts if b != a)]

        for a, (rd, iv) in sorted(pts.items()):
            on = a in front
            ax.scatter(rd, iv, s=110 if on else 44, color=COLORS[a],
                       edgecolor="black" if on else "white",
                       lw=1.4 if on else 0.6, zorder=4 if on else 3, label=a)
        for a in front:
            rd, iv = pts[a]
            ax.annotate(a, (rd, iv), textcoords="offset points", xytext=(0, -16),
                        ha="center", fontsize=7.4, fontweight="bold", color="#006B3C")

        ivs = [v[1] for v in pts.values()]
        lo, hi = min(ivs), max(ivs)
        pad = (hi - lo) * 0.16
        ax.set_ylim(lo - pad * 1.9, hi + pad)
        ax.set_xscale("symlog", linthresh=1000)
        ax.set_xlim(-300, 2.0e6)
        ax.set_xlabel("evidence reads  (symlog; 0 at origin)")
        ax.set_ylabel("integrity violation rate" if E == 64 else "")
        ax.set_title(f"E{E}", fontsize=10, loc="left", fontweight="bold")
        if handles is None:
            handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, fontsize=7.2, ncol=5, loc="lower center",
               bbox_to_anchor=(0.5, -0.10))
    fig.suptitle("Cost buys little integrity: the frontier is occupied by free or near-free policies\n"
                 "outlined + labelled = Pareto-optimal at that horizon",
                 fontsize=9.4, x=0.005, ha="left")
    save(fig, "fig4_cost_frontier")


# ---------------------------------------------------------------- Figure 5
def fig5_accuracy_vs_integrity():
    E = 128
    seeds = valid_seeds("EXP-A001", E)
    fig, ax = plt.subplots(figsize=(5.6, 4.0))
    for a in sorted(COLORS):
        acc = [{r["arm"]: r["metrics"]["canonical_accuracy"]
                for r in cell("EXP-A001", s, E)}[a] for s in seeds]
        iv = [{r["arm"]: r["metrics"]["integrity_violation_rate"]
               for r in cell("EXP-A001", s, E)}[a] for s in seeds]
        ax.errorbar(np.mean(acc), np.mean(iv),
                    xerr=np.std(acc) / np.sqrt(len(acc)), yerr=np.std(iv) / np.sqrt(len(iv)),
                    fmt="o", ms=6, color=COLORS[a], capsize=2, lw=1)
        ax.annotate(a, (np.mean(acc), np.mean(iv)), textcoords="offset points",
                    xytext=(7, -2), fontsize=6.6)
    # The preregistered H3 pair.
    pair = ("last-write-wins", "provenance-regrounding")
    xy = []
    for a in pair:
        acc = np.mean([{r["arm"]: r["metrics"]["canonical_accuracy"]
                        for r in cell("EXP-A001", s, E)}[a] for s in seeds])
        iv = np.mean([{r["arm"]: r["metrics"]["integrity_violation_rate"]
                       for r in cell("EXP-A001", s, E)}[a] for s in seeds])
        xy.append((acc, iv))
    ax.plot([xy[0][0], xy[1][0]], [xy[0][1], xy[1][1]], "-", color="#8B0000", lw=1.6, zorder=1)
    ax.annotate("H3 pair: accuracy indistinguishable,\nintegrity differs (CI excludes 0)",
                xy=((xy[0][0] + xy[1][0]) / 2, (xy[0][1] + xy[1][1]) / 2),
                textcoords="offset points", xytext=(-30, -34), fontsize=7, color="#8B0000",
                arrowprops={"arrowstyle": "->", "color": "#8B0000", "lw": 0.8})
    ax.set_xlabel("canonical accuracy (E128)")
    ax.set_ylabel("integrity violation rate (E128)")
    ax.set_title("Correctness and integrity are not interchangeable", fontsize=8.8, loc="left")
    save(fig, "fig5_accuracy_vs_integrity")


# ---------------------------------------------------------------- Figure 6
def fig6_b001():
    an = json.loads((ROOT / "analysis-audited.json").read_text())
    arms = sorted(an["B001_excess_by_horizon"])
    fig, axes = plt.subplots(1, 2, figsize=(7.8, 3.8))

    ax = axes[0]
    width = 0.35
    xs = np.arange(len(HORIZONS))
    raw_base = [an["B001_descriptive"][str(E)]["no-consolidation"]["net_repair"] for E in HORIZONS]
    raw_cf = [an["B001_descriptive"][str(E)]["counterfactual-recheck"]["net_repair"] for E in HORIZONS]
    ax.bar(xs - width / 2, raw_base, width, label="no-consolidation (inaction)", color="#999999")
    ax.bar(xs + width / 2, raw_cf, width, label="counterfactual-recheck", color="#0072B2")
    ax.axhline(0, color="black", lw=0.9)
    ax.set_xticks(xs); ax.set_xticklabels([f"E{e}" for e in HORIZONS])
    ax.set_ylabel("absolute net repair")
    ax.set_title("Absolute trajectory: positive at short horizons,\nnegative from E32 onward for both arms",
                 fontsize=8.4, loc="left")
    ax.legend(fontsize=7, loc="lower right")

    a2 = axes[1]
    bcol = {"counterfactual-recheck": "#0072B2", "eligibility-trace": "#D55E00",
            "provenance-restricted-blame": "#009E73", "uniform-blame": "#CC79A7"}
    for a in arms:
        ms, los, his = [], [], []
        for E in HORIZONS:
            d = an["B001_excess_by_horizon"][a][str(E)] if str(E) in an["B001_excess_by_horizon"][a] \
                else an["B001_excess_by_horizon"][a][E]
            ms.append(d["mean"]); los.append(d["ci_low"]); his.append(d["ci_high"])
        a2.errorbar(HORIZONS, ms, yerr=[np.array(ms) - np.array(los), np.array(his) - np.array(ms)],
                    fmt="o-", ms=3.6, lw=1.6 if a == "counterfactual-recheck" else 1.1,
                    capsize=2.5, label=a, color=bcol[a],
                    zorder=4 if a == "counterfactual-recheck" else 2)
    a2.axhline(0, color="black", lw=0.9)
    a2.set_xscale("log", base=2); a2.set_xticks(HORIZONS)
    a2.set_xticklabels([str(e) for e in HORIZONS])
    a2.set_xlabel("lifetime length (epochs)")
    a2.set_ylabel("excess net repair vs inaction")
    a2.set_title("Causal contrast: positive, decaying, zero-spanning by E128",
                 fontsize=8.4, loc="left")
    a2.legend(fontsize=6.6, loc="lower right")
    fig.suptitle("A positive causal contrast without absolute repair",
                 fontsize=9.2, x=0.01, ha="left")
    save(fig, "fig6_b001_causal_vs_absolute")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    print("generating figures from", ROOT)
    fig1_concept(); fig2_horizon(); fig3_rank_instability()
    fig4_frontier(); fig5_accuracy_vs_integrity(); fig6_b001()
    print("done")
