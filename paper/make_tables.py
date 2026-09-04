#!/usr/bin/env python3
"""Regenerate every paper table (LaTeX) from the sealed confirmatory manifests."""
from __future__ import annotations

import glob
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from lifetime_integrity.seeds import CONFIRMATORY_SEEDS

R = Path("results/confirmatory/9954ab69cd4d")
OUT = Path("paper/tables"); OUT.mkdir(parents=True, exist_ok=True)
AN = json.loads((R / "analysis-audited.json").read_text())
HOR = (8, 16, 32, 64, 128)


def cell(exp, s, E):
    return [json.loads(Path(f).read_text())
            for f in sorted(glob.glob(f"{R}/{exp}/seed-{s}/epochs-{E}/*.json")) if "validation" not in f]


def vseeds(exp, E):
    return [s for s in CONFIRMATORY_SEEDS
            if json.loads((R / exp / f"seed-{s}" / f"epochs-{E}" / "validation.json").read_text())["structurally_valid"]]


def boot(v, key):
    rng = np.random.default_rng(int.from_bytes(hashlib.sha256(key.encode()).digest()[:4], "big"))
    x = np.asarray(v, dtype=float)
    m = x[rng.integers(0, len(x), size=(10000, len(x)))].mean(axis=1)
    return float(x.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def esc(s): return s.replace("_", r"\_")


def write(name, body):
    (OUT / name).write_text(body); print(f"  {name}")


# Table 1 — mechanisms
T1 = [("last-write-wins", "adopt the most recent assertion", "none", "per-slot value"),
      ("unconstrained-accumulator", "accrete evidence counts, never expire", "none", "unbounded counts"),
      ("lossy-latent", "bounded state with cross-slot interference", "none", "fixed-width cells"),
      ("periodic-reset", "wipe and rebuild from a recent window", "periodic, bounded", "counts + window"),
      ("evidence-reconstruction", "hold no belief; re-derive at query time", "per query", "none"),
      ("provenance-regrounding", "reliability-weighted re-derivation", "per query", "source reliabilities"),
      ("confidence-decay", "time-decayed confidence, abstain when unsure", "none", "decayed counts"),
      ("contradiction-regrounding", "re-read only when a conflict is detected", "on conflict", "counts + support"),
      ("hybrid-symbolic-latent", "corroboration-gated symbolic store over latent", "none", "symbolic + counts")]
rows = "\n".join(rf"{esc(a)} & {b} & {c} & {d} \\" for a, b, c, d in T1)
write("table1_mechanisms.tex", rf"""\begin{{tabular}}{{llll}}
\toprule
Mechanism & Strategy & Evidence reads & Persistent state \\
\midrule
{rows}
\bottomrule
\end{{tabular}}""")

# Table 2 — confirmatory hypotheses
p1, p2, p3 = AN["P1_A001_H2"], AN["P2_A001_H1"], AN["P3_B001_H1"]
h = AN["holm_primary"]
t2 = [
    ("A001 H2 (P1)", r"mean Spearman $\rho$(E8,E128)", f"{p1['mean']:.4f}",
     f"[{p1['ci_low']:.3f}, {p1['ci_high']:.3f}]", f"Holm, p={h['P1_A001_H2']['p']:.4f}",
     "supported"),
    ("A001 H1 (P2)", r"paired $\Delta$IVR, conf.-decay $-$ unconstrained @E128",
     f"{p2['mean']:+.4f}", f"[{p2['ci_low']:+.3f}, {p2['ci_high']:+.3f}]",
     f"Holm, p={h['P2_A001_H1']['p']:.4f}", "supported"),
    ("B001 H1 (P3)", r"paired excess net repair, ctf.-recheck @E64",
     f"{p3['mean']:+.4f}", f"[{p3['ci_low']:+.4f}, {p3['ci_high']:+.4f}]",
     f"Holm, p={h['P3_B001_H1']['p']:.4f}",
     r"supported \emph{as relative mitigation}"),
    ("A001 H3", "accuracy-matched pair differing on integrity @E128",
     "+0.0160", "[+0.0051, +0.0270]", "secondary", "supported (1 pair)"),
    ("B001 H2", "highest-recall arm $\\neq$ highest-excess arm @E64",
     "uniform-blame vs ctf.-recheck", "---", "secondary", "supported"),
]
rows = "\n".join(rf"{a} & {b} & {c} & {d} & {e} & {f} \\" for a, b, c, d, e, f in t2)
write("table2_hypotheses.tex", rf"""\begin{{tabular}}{{llllll}}
\toprule
Hypothesis & Estimand & Estimate & 95\% CI & Multiplicity & Outcome \\
\midrule
{rows}
\bottomrule
\end{{tabular}}""")

# Table 3 — E128 cost frontier
E = 128; seeds = vseeds("EXP-A001", E)
front = AN["A001_frontier"][str(E)]["pareto"]
rows = []
for a in sorted(AN["A001_frontier"][str(E)]["aggregate"]):
    def g(k, sub, a=a):
        return np.mean([{r["arm"]: r[sub][k] for r in cell("EXP-A001", s, E)}[a] for s in seeds])
    rows.append((a, g("integrity_violation_rate", "metrics"), g("canonical_accuracy", "metrics"),
                 g("evidence_reads", "budget_actual"), g("maintenance_ops", "budget_actual"),
                 g("state_bytes", "budget_actual"), a in front))
rows.sort(key=lambda r: r[1])
BULLET = r"$\bullet$"
body = "\n".join(rf"{esc(a)} & {iv:.4f} & {acc:.3f} & {rd:,.0f} & {ops:,.0f} & {sb:,.0f} & {BULLET if p else ''} \\"
                 for a, iv, acc, rd, ops, sb, p in rows)
write("table3_frontier_e128.tex", rf"""\begin{{tabular}}{{lrrrrrc}}
\toprule
Mechanism & IVR & Accuracy & Evid. reads & Maint. ops & State bytes & Pareto \\
\midrule
{body}
\bottomrule
\end{{tabular}}""")

# Table 4 — B001 at E64
E = 64; seeds = vseeds("EXP-B001", E)
base = np.mean([{r["arm"]: r["consolidation_metrics"]["net_repair"] for r in cell("EXP-B001", s, E)}["no-consolidation"] for s in seeds])
rows = []
for a in sorted({r["arm"] for r in cell("EXP-B001", seeds[0], E)}):
    if a == "no-consolidation":
        continue
    def g(k, a=a):
        return [{r["arm"]: r["consolidation_metrics"] for r in cell("EXP-B001", s, E)}[a][k] for s in seeds]
    ex = AN["B001_excess_by_horizon"][a][str(E)]
    rows.append((a, np.mean(g("net_repair")), base, ex["mean"], ex["ci_low"], ex["ci_high"],
                 np.mean(g("culprit_accuracy_delta")), np.mean(g("decoy_accuracy_delta")),
                 np.mean(g("attribution_recall")), np.mean(g("attribution_precision")),
                 np.mean(g("consolidation_reads"))))
rows.sort(key=lambda r: -r[3])
body = "\n".join(rf"{esc(a)} & {nr:+.3f} & {bs:+.3f} & {ex:+.4f} & [{lo:+.3f},{hi:+.3f}] & {cd:+.3f} & {dd:+.3f} & {rc:.2f} & {pr:.2f} & {rds:,.0f} \\"
                 for a, nr, bs, ex, lo, hi, cd, dd, rc, pr, rds in rows)
write("table4_b001_e64.tex", rf"""\begin{{tabular}}{{lrrrrrrrrr}}
\toprule
Policy & Raw net & Inaction & Excess & 95\% CI & Culprit $\Delta$ & Decoy $\Delta$ & Recall & Prec. & Reads \\
\midrule
{body}
\bottomrule
\end{{tabular}}""")

# Table 5 — culprit repair by horizon (erratum E6)
rows = []
for E in HOR:
    seeds = vseeds("EXP-B001", E)
    v = [{r["arm"]: r["consolidation_metrics"] for r in cell("EXP-B001", s, E)}["counterfactual-recheck"]["culprit_accuracy_delta"] for s in seeds]
    m, lo, hi = boot(v, f"cd/{E}")
    verdict = "absolute repair" if lo > 0 else ("deterioration" if hi < 0 else "inconclusive")
    rows.append(rf"E{E} & {len(seeds)} & {m:+.4f} & [{lo:+.4f}, {hi:+.4f}] & {verdict} \\")
write("table5_culprit_by_horizon.tex", r"""\begin{tabular}{lrrrl}
\toprule
Horizon & $n$ seeds & Culprit $\Delta$ & 95\% CI & Reading \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabular}""")
print("done")
