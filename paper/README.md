# Manuscript

Working draft of the Lifetime Integrity paper. Everything is regenerated from the
sealed confirmatory manifests under `results/confirmatory/9954ab69cd4d/`.

```bash
PYTHONPATH=src python paper/make_figures.py      # figures/*.pdf, *.png
PYTHONPATH=src python paper/make_tables.py       # tables/*.tex
PYTHONPATH=src python paper/make_provenance.py   # provenance.json
pdflatex -output-directory=paper paper/main.tex  # requires a LaTeX toolchain
```

**No value in `main.tex` is hand-copied from a chart.** Every table is `\input`
from `tables/`, and every figure is a generated PDF.

## Status

- Draft prose complete; figures and tables generated and inspected.
- **Not compiled**: no LaTeX toolchain was available in the authoring
  environment, so `main.tex` has never been run through `pdflatex`. Expect the
  usual first-compile fixes.
- Manuscript-audit errata E4–E6 are recorded in
  `../experiments/PHASE-3-CONFIRMATORY-RESULT.md` and reflected in the prose.

## Counting units

| unit | count |
|---|---|
| comparison cells (12 seeds × 5 horizons × 2 experiments) | 120 |
| logical arm-runs (540 A001 + 300 B001) | **840** |
| stored JSON artifacts | 963 |
| secondary execution passes | 0 |
