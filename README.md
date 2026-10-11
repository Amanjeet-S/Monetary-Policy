# ECB policy and information surprises in German consumer-goods production

## 1. Question

I investigate whether separating monetary-policy and information components changes the estimated response of German durable relative to non-durable consumer-goods production. The [research design](docs/research_design.md) defines the comparison, its economic interpretation and the fixed specification. The [source register](docs/sources.md) positions it against published research and records the material actually consulted.

## 2. Evidence and status

The project is being redesigned around cumulative US household purchases, using direct expenditure measures and a published narrative policy record. The [prospective US design](docs/us_purchase_design.md) fixes the new analysis before spending estimation. The German studies remain retained. The current manuscript records the earlier evidence and is not a completed submission paper.

The [data audit](docs/data_audit.md) resolves the three event exclusions, verifies monthly aggregation and independently reconstructs the supplied shocks. A new [10 October snapshot](data/raw/2026-10-10/manifest.json) adds August 2026 production and preserves the [September vintage](data/raw/2026-09-15/manifest.json) unchanged. The [primary specification](docs/primary_specification.json) is recorded before fitting responses. The [results note](docs/results.md) reports the primary estimates and all declared sensitivities, independently checked in R. The [working paper](paper/monetary_policy.pdf), with its [editable source](paper/monetary_policy.tex), develops the durable-stock mechanism, matched evidence, joint stability tests, complete retained-factor rotation assessment and causal sensitivity, with appendix proofs.

## 3. Reproduction

From the repository root, with Python 3.11 or later:

```sh
python3 scripts/check_repository.py
python3 scripts/audit_germany_data.py
python3 scripts/build_monthly_panel.py
```

The [development guide](docs/development.md) provides notebook execution and the optional source-reconstruction command. The [data guide](data/README.md) documents inputs and generated fields. These initial reproduction commands use retained data and require no credentials or download.

## 4. Research package

The current working paper is twenty pages, including appendices and bibliography. The appendices precede the references. The [paper manifest](paper/manifest.json) identifies the matching source and PDF. Code, an executable notebook and independent numerical checks support the evidence, including the complete supplementary inference. [Licensing](LICENSING.md), [third-party notices](THIRD_PARTY_NOTICES.md) and [provenance](PROVENANCE.md) identify the applicable rights and origins.
