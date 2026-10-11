# Monetary tightening and cumulative household purchases

## 1. Research

I assess whether the first-year reduction in US consumer-durable purchases following monetary tightening is offset during the next two years. The study uses the original meeting-level policy and pre-decision forecast record, monthly household quantity measures and joint uncertainty for early, later and cumulative responses.

The primary durable shortfall is negative but sensitive in precision to longer policy histories and leverage adjustment. Services have a smaller cumulative contraction across the declared checks. A prespecified exclusion of reserves-targeting decision origins gives a larger durable deficit; the subsequent joint sample comparison is exploratory and does not identify a causal operating-regime effect.

The [paper](paper/monetary_policy.pdf) and [editable LaTeX source](paper/monetary_policy.tex) contain the economic mechanism, estimates, interpretation and two appendices before the references. The [paper manifest](paper/manifest.json) records matching hashes, authorship and page count.

## 2. Reproduction

Use a complete Git checkout and Python 3.11 or later. Install the pinned environment with `python -m pip install -r requirements.lock`, then run:

```sh
python scripts/build_us_purchase_panel.py
python scripts/us_purchases.py --check
python scripts/us_purchase_diagnostics.py --check
python scripts/check_repository.py
```

These commands use retained source bytes without credentials or downloads. The [data guide](data/README.md), [source register](docs/sources.md), [prospective design](docs/us_purchase_specification.json) and [informed follow-up record](docs/us_purchase_followup_specification.json) specify measurement and chronology. Independent R reconstruction checks all retained cases, inverse-set topologies and the overlapping-sample contrast through the [research workflow](.github/workflows/research.yml).

## 3. Research record

The [research design](docs/us_purchase_design.md) explains the scope and identifying assumptions. Earlier German announcement and future-policy studies, including their inconclusive findings, remain intact at the [preserved study revision](https://github.com/Amanjeet-S/Monetary-Policy/tree/german-studies-2026-10-11). Their original hashes are verified from Git history. The current working tree presents the US study.

[Provenance](PROVENANCE.md), [licensing](LICENSING.md) and [third-party notices](THIRD_PARTY_NOTICES.md) preserve authorship and source rights. PDF export uses the saved standalone source with `python scripts/build_paper.py --compile` when XeLaTeX is installed.
