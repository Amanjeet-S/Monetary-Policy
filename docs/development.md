# Reproduction

## 1. Retained-data checks

Use Python 3.11 or later and the commands in the [README](../README.md). They verify documentation links and both source vintages, report active coverage, and create `data/processed/monthly_panel.csv` and `reports/panel_build.json`. The panel has no imputation, outcome transformation or estimation. Generated files remain outside Git.

## 2. Declared notebook environment

```sh
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock -r requirements-notebooks.lock
python scripts/execute_notebooks.py
```

On Windows, activate with `.venv\Scripts\Activate.ps1`. Notebook execution uses a fresh kernel and preserves the saved file unless `--write` is supplied. The GitHub workflow runs the retained-data checks and notebook on Python 3.11 and 3.13.

## 3. Optional source reconstruction

Download the eight unchanged files listed in the [review metadata](../data/metadata/shock_source_review_2026-10-10.json) to their stated relative paths under a directory outside the repository. Then run:

```sh
python scripts/reconcile_shock_sources.py --evidence /absolute/path/to/source-files
```

The full reconstruction uses the declared NumPy dependency; `--skip-construction` permits standard-library coverage and aggregation checks. The metadata pins hashes and the author revision. The ECB workbook URL is mutable, so a later download may fail the recorded hash check. These external files and copyrighted paper texts are not redistributed here. The self-contained manuscript source includes its bibliography and vector figures.

## 4. Fixed empirical analysis

A full Git history, included by a standard clone, is required to verify the pre-estimation revision. `python scripts/run_analysis.py` recreates the primary comparison, declared sensitivities, machine-readable estimates and both figures in `results/`. The [fixed record](primary_specification.json) remains unchanged; the [results note](results.md) reports interpretation and limitations. The [analysis notebook](../notebooks/monetary_transmission.ipynb) executes the same calculation in a fresh kernel. Use `PYTHONPATH=scripts python -m pytest -q tests` for the mathematical domain and covariance checks.

The independent check uses base R 4.6.1, without additional R packages:

```sh
Rscript scripts/verify_local_projections.R . reports/r_estimates.csv
python scripts/compare_r_results.py results/estimates.csv reports/r_estimates.csv --report reports/r_verification.json
```

The pinned GitHub workflow runs this check in an isolated environment and retains its numerical report. Agreement assesses transformations, samples, coefficients, joint covariance and interval construction; it does not validate causal assumptions. Source vintages, the supplied decomposition and its identification uncertainty are kept distinct from ordinary projection uncertainty.

## 5. Manuscript numerical blocks

`python scripts/build_paper.py` refreshes the eight numerical table and figure blocks in `paper/monetary_policy.tex` from the retained estimates and sample description. It preserves the surrounding research text and its layout choices. The source is self-contained and can be compiled without additional project files. The [final PDF](../paper/monetary_policy.pdf) and editable source are identified by the [paper manifest](../paper/manifest.json).

`python scripts/describe_primary_sample.py` reproduces the post-estimation sample description without fitting outcomes. Use `--check` to compare its moments and input hashes with the retained summary. The table reports the reporting unit against observed monthly variation; it does not change the primary normalisation or confidence procedure.

`python scripts/gap_followup.py` reproduces the six-case supplementary calculation from unchanged estimates. Use `--check` for retained-result verification. The independent check uses `Rscript scripts/verify_gap_followup.R reports/r_estimates.csv reports/r_gap_followup.csv`, followed by `python scripts/gap_followup.py --check --compare-r reports/r_gap_followup.csv`. It checks the p-values and joint-region extrema with a separate numerical method, without additional outcome regressions.

The declared identification extension is reproduced without downloads:

```sh
python scripts/joint_stability.py --check
python scripts/rotation_sensitivity.py --check
python scripts/causal_sensitivity.py --check
Rscript scripts/verify_joint_stability.R . reports/r_stability.csv reports/r_regime.csv
Rscript scripts/verify_rotation_sensitivity.R . reports/r_rotation.csv
Rscript scripts/verify_causal_sensitivity.R . reports/r_causal.csv
python scripts/compare_extension_r.py --r-stability reports/r_stability.csv --r-regime reports/r_regime.csv --r-rotation reports/r_rotation.csv --r-causal reports/r_causal.csv --output reports/extension_verification.json
```

The R checks independently reconstruct coefficients, joint covariance, nonlinear confidence images, continuum envelopes and predetermined-outcome tests. The rotation grid is a numerical check; analytic endpoint and corner arguments determine the reported ranges. The existing notebook retains the locked analysis; these extension commands reproduce the additional evidence.

`python scripts/build_paper.py --compile` exports a matching PDF when XeLaTeX is available. The source enforces the twenty-page total; every updated export requires a fresh layout review.
