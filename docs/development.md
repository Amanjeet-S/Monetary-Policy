# Reproduction and development

## 1. Source audit and monthly alignment

The initial scripts use the standard library and support Python 3.11 or later. From the repository root:

```sh
python3 scripts/check_repository.py
python3 scripts/audit_germany_data.py
python3 scripts/build_monthly_panel.py
```

The first command checks tracked Markdown links and retained source hashes. The second reports source coverage. The third repeats the source audit and creates `data/processed/monthly_panel.csv` and `reports/panel_build.json`. Generated files remain outside version control and can be recreated from the fixed snapshot. These commands require no provider credentials or new data download.

## 2. Notebook environment

The migrated dependency locks support the initial notebook and preserve the declared environment from the source repository. They are not a completed estimation environment. For the notebook, use Python 3.11 or 3.13:

```sh
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock -r requirements-notebooks.lock
python scripts/execute_notebooks.py
```

On Windows, activate with `.venv\Scripts\Activate.ps1`. The notebook runner executes the coverage notebook in a fresh kernel and leaves the saved file unchanged unless `--write` is supplied. The GitHub workflow runs the documentation checks, data audit, panel construction and notebook execution on Python 3.11 and 3.13. A workflow definition does not itself establish that a remote run has passed.

## 3. Changes and interpretation

I retain source files unchanged and record any new downloads in a separate dated directory with their own metadata and hashes. New data must come from free sources or existing authorised institutional access at no additional cost. I record unsuccessful checks and material limitations alongside successful results.

The initial monthly panel has no outcome transformation, renormalisation, imputation or estimation. Available index dates define its calendar; blank cells preserve unavailable inputs. `derived_event_count` counts rows in the retained derived event file within its coverage window, including months with zero such rows. It does not identify omitted ECB events or establish complete event coverage. The [research design](research_design.md) must be resolved before treating the panel as an estimation sample.
