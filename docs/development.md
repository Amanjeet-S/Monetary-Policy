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

The full reconstruction uses the declared NumPy dependency; `--skip-construction` permits standard-library coverage and aggregation checks. The metadata pins hashes and the author revision. The ECB workbook URL is mutable, so a later download may fail the recorded hash check. These external files and copyrighted paper texts are not redistributed here. The completed analysis will add the R comparison and commands regenerating its tables, figures and LaTeX/PDF.
