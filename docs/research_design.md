# Research design

## 1. Design stage

I have not locked the specification or inspected main estimates. I will record and commit the primary specification before fitting the main model. This document preserves the feasibility-stage question and unresolved methodological choices; it is not a preregistration of a completed design.

## 2. Question and measurement

I ask how unexpected ECB monetary tightening changes German durable consumer-goods production relative to non-durable consumer-goods production. Eurostat's `MIG_DCOG` and `MIG_NDCOG` identify consumer-goods production groups, rather than household consumption or the broader US manufacturing categories. The [source register](sources.md) and [data audit](data_audit.md) record the classifications, index units, seasonal adjustment and retrieval vintage.

My primary estimand will be the difference between the two production responses at one declared horizon. Twelve months is a candidate, subject to the methodological review. A limited response path will provide context. I will choose the horizon, output transformation, sample rules, lags and controls before the main estimation, with an explicit account of the economic and statistical rationale.

## 3. Identification and shock construction

I plan to use the author-maintained update of the decomposition of [Jarociński and Karadi (2020)](https://doi.org/10.1257/mac.20180090), distinguishing monetary-policy shocks from central-bank information shocks. The [source register](sources.md) records that the publisher's abstract and update documentation were consulted, while a full-text methods review remains outstanding. I will review the sign restrictions, event windows, normalisation, aggregation and the distinction between the supplied decompositions before choosing a primary measure. Published identification methods require assumptions; their use does not automatically establish exogeneity in this application.

The feasibility audit recorded 315 dated observations in the inspected raw EA-MPD workbook and 312 rows in the derived event file. I will reconcile those observations against the source documentation and construction code, retaining any exclusion reasons. The raw workbook was inspected previously and is not included in this snapshot. The panel's derived event counts describe only the retained event file and cannot resolve this discrepancy. Missing events must not silently become zero shocks; no-event months, measured zero surprises and missing observations have different meanings.

## 4. Estimation and inference

I plan to use local projections following [Jordà (2005)](https://doi.org/10.1257/0002828053828518). The [source register](sources.md) records consultation of publisher metadata and the abstract only; full-text review of the method and inference remains outstanding. I will derive a parsimonious specification for this application, justify the outcome transformation using time-series properties, state the shock scale, and document the predetermined control set.

I will estimate the response difference directly or use a joint procedure preserving covariance between the two series. One significant response and one insignificant response do not establish a significant difference. The inference procedure must address persistent outcomes, serial dependence and overlapping horizons. I will distinguish uncertainty at the primary horizon from simultaneous inference across a response path, and discuss the uncertainty attached to estimated and identified shocks.

## 5. Robustness and interpretation

I will prespecify a small set of checks for lag length, shock decomposition, influential events and crisis-period sensitivity. I will report the observations retained at each horizon and explain losses from transformations, controls and exclusions. A fixed-composition euro-area comparison remains optional and requires an additional metadata review. Common ECB shocks would not provide independent replications across countries.

I will interpret potential export, inventory and supply mechanisms without claiming to identify them separately. Imprecise, contrary and sensitive results belong in the evidence. The intended project-specific contribution is an empirical response contrast and an assessment of what its assumptions and precision permit me to conclude. Neither sophisticated implementation nor a familiar result establishes theoretical novelty.

## 6. Specification record and completion

Before estimation, I will add a dated specification record containing the primary horizon, shock field and scale, outcome formula, sample dates, missing-data and exclusion rules, regressors, lag order, inference method and limited robustness set. I will identify the commit that freezes this record and explain subsequent departures.

Completion requires an auditable estimation sample, a literature-grounded specification, independently checked estimates and uncertainty calculations, reproducible tables and figures, and a paper with explicit limitations. The current notebook and panel establish source access and data alignment only. The [writing-sample plan](writing_sample_plan.md) records the remaining sequence and provisional drafting targets.
