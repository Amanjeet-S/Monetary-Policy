# Source data

## 1. Snapshots

[10 October 2026](raw/2026-10-10/manifest.json) is the active vintage; [15 September 2026](raw/2026-09-15/manifest.json) preserves the initial retrieval. Each manifest records URLs, units, attribution, reuse conditions and exact hashes. Eurostat supplies observed production and price indices. The Jarociński update supplies estimated policy and information contributions from announcement-window financial data. Providers retain their own rights, as recorded in [third-party notices](../THIRD_PARTY_NOTICES.md).

The [data audit](../docs/data_audit.md) states coverage, revisions, classifications, exclusions, units and zero/missingness conventions. External source-review files are described by [metadata](metadata/shock_source_review_2026-10-10.json) and retained separately. New vintages must be added without replacing existing bytes.

## 2. Generated panel

`python scripts/build_monthly_panel.py` creates `data/processed/monthly_panel.csv` and `reports/panel_build.json`. Fields retain the three index levels, six provider shock measures, event counts and complete-input coverage. Empty cells preserve missing inputs, while provider shock strings retain recorded zeros. An event count refers to the retained source definition, including its documented exclusions. The [research design](../docs/research_design.md) determines the final transformations, estimation sample and inference. Generated files are excluded from Git.
