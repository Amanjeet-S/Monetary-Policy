# Germany monetary-policy data snapshot

## 1. Retained sources

The `raw/2026-09-15/` directory contains unchanged public source files for the initial coverage audit. The [source manifest](raw/2026-09-15/manifest.json) records URLs, checksums, units, attribution and reuse conditions. Access date: 15 September 2026.

| Source | Files | Meaning |
| --- | --- | --- |
| Eurostat, `sts_inpr_m` | `eurostat_DE_MIG_DCOG.json`, `eurostat_DE_MIG_NDCOG.json` | German monthly consumer-goods production, seasonally and calendar adjusted, 2021=100 |
| Eurostat, `prc_hicp_midx` | `eurostat_hicp_DE.json` | German all-items HICP, historical classification, 2015=100 |
| Marek Jarociński, update of Jarociński and Karadi (2020) | `jk_ecb_monthly.csv`, `jk_ecb_events.csv` | Published-method monetary-policy and information-shock estimates, supplied at monthly and event frequencies |

Run `python scripts/audit_germany_data.py` from the repository root. The audit reads the snapshot without network access, verifies hashes and reports coverage. It does not estimate policy effects or impute missing data. Production and prices are observed official indices; the shock series are research estimates derived from financial-market observations.

The data retain the original providers' rights. Source: Eurostat, [industrial production](https://ec.europa.eu/eurostat/databrowser/view/sts_inpr_m/default/table?lang=en) and [HICP](https://ec.europa.eu/eurostat/en/web/products-datasets/-/PRC_HICP_MIDX). Eurostat's [reuse notice](https://ec.europa.eu/eurostat/help/copyright-notice) requires source acknowledgement. The [Jarociński dataset](https://github.com/marekjarocinski/jkshocks_update_ecb) is CC BY 4.0; cite Jarociński and Karadi (2020), DOI 10.1257/mac.20180090. No upstream code or paper text is copied here.

This is a fixed research snapshot. The URLs can return later revisions. New downloads must go in a new dated directory with new metadata rather than overwrite these files.

## 2. Generated monthly panel

Running `python scripts/build_monthly_panel.py` from the repository root creates `data/processed/monthly_panel.csv` and `reports/panel_build.json`, with both paths relative to the repository root. The CSV contains source indices, the six supplied monthly shock measures, derived event counts and a flag identifying months with all three indices and supplied shocks. It has an outer calendar join, no imputation, no outcome transformation and no estimation. Blank shock cells outside the supplied period remain blank. Recorded negative zeros retain their provider spelling.

The event counts describe the retained derived file within its coverage window, rather than a verified complete ECB announcement calendar. The unresolved 315 versus 312 discrepancy remains a design task. The report records raw and generated hashes and the common-source interval. Generated files are reproducible and excluded from Git. The [research design](../docs/research_design.md) determines whether and how these observations can become an estimation sample.
