# ECB monetary policy and consumer-goods production in Germany

## 1. Research purpose

I investigate how unexpected ECB monetary tightening affects German durable relative to non-durable consumer-goods production. I am developing this quantitative economics project as a focused research paper. The intended contribution is a focused empirical comparison supported by transparent identification, econometric inference and reproducible evidence. I do not claim a new identification method or theoretical result.

The principal estimand is the difference between the two production responses at a horizon declared before the main estimation. Production reflects exports, inventories and supply conditions as well as domestic demand, so this comparison cannot separately identify a household-consumption channel. The [research design](docs/research_design.md) records the unresolved choices and the [writing-sample plan](docs/writing_sample_plan.md) defines the route to a finished paper.

## 2. Current status

The attributed source snapshot, coverage audit and initial monthly data alignment are available. The snapshot contains 322 common monthly observations from January 1999 to October 2025 before transformations, lags and response-horizon losses. All five retained source files are checked against their original SHA-256 hashes. No local-projection estimates or causal findings have been produced, and the primary specification is not locked.

The next research milestone is to reconcile event exclusions, review the published identification and inference methods, and record the primary specification before estimation. Python will implement the analysis; selected estimates and uncertainty calculations will subsequently be checked independently in R. The current code supports source auditing and data alignment only.

## 3. Reproduction

The source audit and panel construction use the Python standard library and require no download or credentials. From this repository's root, with Python 3.11 or later:

```sh
python3 scripts/check_repository.py
python3 scripts/audit_germany_data.py
python3 scripts/build_monthly_panel.py
```

The panel retains the source indices and supplied monthly shock measures without transformation or imputation. Generated files are written to `data/processed/` and `reports/` and remain outside Git. The [development guide](docs/development.md) describes the optional notebook environment and fresh execution of the [coverage notebook](notebooks/data_coverage.ipynb). The [data audit](docs/data_audit.md) and [data guide](data/README.md) state the measurement and coverage limits.

## 4. Evidence and provenance

The [source register](docs/sources.md) records publication details and the versions actually consulted. The [migration record](PROVENANCE.md) identifies the source repository revision and preserved snapshot. The source files remain unchanged; path changes and subsequent work are recorded separately. Prior consultation records have not been upgraded to full-text reviews by this migration.

This repository is private. Free sources and existing authorised institutional access are the permitted acquisition routes. [Third-party notices](THIRD_PARTY_NOTICES.md) and [licensing](LICENSING.md) retain the applicable rights in migrated material. A private repository does not change permissions already granted for previously released material.

## 5. Writing sample

The paper will connect an economic question to a defined estimand, explain the identifying assumptions, report uncertainty for the response difference, and assess sensitivity to a small prespecified robustness set. I will distinguish established methods, any checked project-specific derivations, numerical findings and interpretation. The intended argument remains to be established by retained evidence. A twenty-page paper and a 2,000-word version are provisional internal drafting targets.

## 6. Keywords

Monetary economics; ECB monetary policy; Germany; consumer-goods production; local projections; econometric inference.
