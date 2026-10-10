# ECB monetary policy and consumer-goods production in Germany

## 1. Research question

I investigate how unexpected ECB monetary tightening affects German durable relative to non-durable consumer-goods production. The paper will explain the economic problem, derive its empirical comparison, and develop an original argument from checked mathematics and retained evidence. The [research design](docs/research_design.md) records the proposed estimand and unresolved choices; the [research plan](docs/research_plan.md) sets the research and presentation requirements.

Production reflects exports, inventories and supply conditions as well as domestic demand. The response difference therefore requires an explicit account of its identifying assumptions and economic interpretation. Its contribution must be established against the relevant published literature before estimation and writing are treated as complete.

## 2. Current evidence

The attributed source snapshot, coverage notebook and initial monthly panel are available. The production, price and shock series overlap for 322 months from January 1999 to October 2025 before transformations, lags and response-horizon losses. The five source files retain their original SHA-256 hashes. Specification, estimation, full-text methodological review and the paper remain outstanding.

The [source register](docs/sources.md) records the versions actually consulted. The [data audit](docs/data_audit.md) identifies coverage and unresolved event exclusions. The [migration record](PROVENANCE.md) preserves the original snapshot and repository revision. This repository contains all inputs needed for the initial audit and panel construction.

## 3. Reproduction

From the repository root, with Python 3.11 or later:

```sh
python3 scripts/check_repository.py
python3 scripts/audit_germany_data.py
python3 scripts/build_monthly_panel.py
```

These scripts require no credentials or download. The generated panel retains source index levels, supplied shock measures and missing inputs. The [development guide](docs/development.md) provides the optional notebook environment and fresh execution command for the [coverage notebook](notebooks/data_coverage.ipynb). The [data guide](data/README.md) explains the fields and generated files.

## 4. Research package

The finished project will include a concise LaTeX paper and matching PDF, an executable notebook, analysis code, independently checked estimates and uncertainty calculations, and reproducible figures and tables. Every display will support a stated part of the economic argument. The paper will use British English, first person singular for my research choices, numbered sections, author–date references and keywords immediately after the abstract.

This repository is private. Original and third-party rights are recorded in [licensing](LICENSING.md) and [third-party notices](THIRD_PARTY_NOTICES.md). Research development uses free sources or existing authorised access at no additional cost.

## 5. Keywords

Monetary economics; ECB monetary policy; Germany; consumer-goods production; local projections; econometric inference.
