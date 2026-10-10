# ECB policy and information surprises in German consumer-goods production

## 1. Question

I investigate whether separating monetary-policy and information components changes the estimated response of German durable relative to non-durable consumer-goods production. The [research design](docs/research_design.md) defines the comparison, its economic interpretation and the remaining specification choices. The [source register](docs/sources.md) positions it against published research and records the material actually consulted.

## 2. Evidence and status

The [data audit](docs/data_audit.md) resolves the three event exclusions, verifies monthly aggregation and independently reconstructs the supplied shocks. A new [10 October snapshot](data/raw/2026-10-10/manifest.json) adds August 2026 production and preserves the [September vintage](data/raw/2026-09-15/manifest.json) unchanged. Specification locking, main estimation and the paper remain outstanding.

## 3. Reproduction

From the repository root, with Python 3.11 or later:

```sh
python3 scripts/check_repository.py
python3 scripts/audit_germany_data.py
python3 scripts/build_monthly_panel.py
```

The [development guide](docs/development.md) provides notebook execution and the optional source-reconstruction command. The [data guide](data/README.md) documents inputs and generated fields. These initial reproduction commands use retained data and require no credentials or download.

## 4. Research package

The paper will contain the economic argument and evidence, with long proofs and derivations in appendices. Its complete length, including appendices and bibliography, will not exceed twenty pages. Code, an executable notebook and matching LaTeX/PDF versions will support the findings. [Licensing](LICENSING.md), [third-party notices](THIRD_PARTY_NOTICES.md) and [provenance](PROVENANCE.md) identify the applicable rights and origins.
