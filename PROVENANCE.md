# Sources and migration provenance

## 1. Origin

I separated this project from [Quantitative-Finance](https://github.com/Amanjeet-S/Quantitative-Finance) on 10 October 2026. The source checkout was clean at commit `281e007cb89673fa49270bd5c92a636080a369c3`. The migrated project was `projects/germany_monetary_policy/`, with data under `data/public/germany_monetary_policy/` and associated audit scripts. The source repository's unrelated studies, private inputs and full Git history have not been imported.

The source register and data audit retain their earlier consultation and retrieval records. I adapted local paths, organised the single-project layout, re-executed the coverage notebook in a fresh kernel, and added a research plan and untransformed monthly panel construction. These changes do not constitute new consultation of the cited paper texts.

## 2. Source data

The snapshot was retrieved on 15 September 2026. Its five source files and `manifest.json` were copied byte for byte to [data/raw/2026-09-15](data/raw/2026-09-15/manifest.json). The manifest retains the original URLs, retrieval dates, units, attribution and SHA-256 hashes. The source audit verifies these hashes before data alignment. I do not overwrite this snapshot with later revisions.

The [source register](docs/sources.md) identifies the published economic literature and the versions actually consulted. The [data audit](docs/data_audit.md) records coverage and unresolved choices. Eurostat observations and the author-maintained ECB shock estimates retain their providers' attribution and reuse conditions, as stated in [third-party notices](THIRD_PARTY_NOTICES.md).

## 3. Research status

The migrated material established data access and coverage. The added panel aligns observed dates and retains missing inputs. Neither establishes a causal result, a locked specification or a complete literature review. I will record future transformations, exclusion rules, methodological sources and interpretation at the relevant stage.

## 4. Migration record

The machine-readable [migration record](migration.json) contains the full source commit, source paths, destination paths and source hashes for the retained raw files. My original repository remains the provenance source for migrated material; subsequent work is versioned in this private repository.
