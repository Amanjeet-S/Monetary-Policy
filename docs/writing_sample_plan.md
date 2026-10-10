# Writing-sample development plan

## 1. Purpose and present status

I intend to develop this project as a quantitative economics writing sample. I aim to demonstrate that I can formulate a precise economic question, justify an empirical design, implement and verify an estimator, and interpret evidence within the limits of its assumptions. This document is an initial research plan. It is not a paper, and the retained data audit does not establish any monetary-policy effect.

The [research design](research_design.md) records the proposed comparison and unresolved choices. The [data audit](data_audit.md) establishes source coverage and the integrity of the retained snapshot. The [source register](sources.md) distinguishes published methodological foundations from the author-maintained shock update and records which source versions and material have actually been consulted.

## 2. Question and intended contribution

I ask how unexpected ECB monetary tightening changes German durable consumer-goods production relative to non-durable consumer-goods production. My principal empirical comparison will be the difference between their responses at one prespecified horizon. A limited response path will provide context, while a small set of declared robustness checks will assess the sensitivity of the comparison.

The production indices measure consumer-goods production rather than household consumption. Production can reflect exports, inventories and supply conditions. I therefore cannot interpret a response difference as a separately identified household-consumption channel. Nor would a statistically significant response for one production group and an insignificant response for the other establish a significant difference between them.

I will seek a modest, project-specific contribution through a carefully defined response contrast and a transparent assessment of the evidence supporting it. I will distinguish established identification and estimation methods, any application-specific derivations, numerical findings and my interpretation. I will not claim theoretical novelty without a checked comparison with the published literature. The sophistication of the implementation will not itself constitute an original contribution.

## 3. Evidence package

I will preserve the unchanged public source snapshot, its download metadata, checksums and attribution. I will document event exclusions, shock definitions, transformations, sample construction and horizon-specific observation losses. A source-consultation record will identify the version, sections and methodological material used for each relevant claim. References to published articles will not imply that I have reviewed their full text where only metadata, abstracts or repository documentation have been consulted.

My empirical package will include the locked primary specification, reproducible sample construction, estimation code, an independently implemented check of selected estimates, and generated figures and tables. I will report the principal response difference with uncertainty appropriate to the chosen specification. I will distinguish inference at the primary horizon from any simultaneous inference across horizons and retain imprecise or contrary findings. The written sample and its supporting materials will explain what each comparison identifies and which conclusions its assumptions do not support.

## 4. Development sequence

I will first resolve the source and methodological issues recorded in the [data audit](data_audit.md) and [research design](research_design.md). This stage includes reconciling the recorded 315 dated raw EA-MPD observations with the 312 derived events, reviewing monthly aggregation and event exclusions, distinguishing missing observations from no-event months, and establishing the chosen shock decomposition, sign and scale. I will review the production and price metadata, including seasonal adjustment and revisions. I will also complete the necessary full-text review of the published identification, local-projection and inference foundations, recording the material actually consulted.

I will then lock the primary estimand and specification before inspecting the main estimates. I will declare the response horizon, outcome transformation, lag structure, controls, sample rules, shock normalisation and inference procedure. I will derive the response contrast for the chosen specification and preserve cross-series covariance when calculating its uncertainty. I will state a limited robustness set and explain why each check addresses a material assumption.

After the design is locked, I will construct the analysis sample, estimate the responses and verify the implementation. I will independently check selected estimates in R using the same sample, transformations, scaling and conventions as the Python implementation. I will examine influential observations, precision and the declared sensitivity checks, documenting any departures from the initial specification and their reasons. Shared policy shocks in any additional geographical comparison will not constitute independent replications.

I will write the paper after the evidence and verification are available. I will develop the economic argument around the primary comparison, placing its findings alongside the relevant published literature and stating the limits of the interpretation. The current internal drafting targets are a paper of up to twenty pages and a shorter version of up to 2,000 words. These targets are provisional and will be checked against the final paper's presentation requirements.

## 5. Completion criteria

I will regard the project as a completed writing sample when the source and event-coverage questions are resolved or explicitly bounded, the methodological claims are supported by a documented published-literature review, the primary specification is locked, and the estimates and their uncertainty are reproducible and independently checked. The figures and tables must be generated from the retained analysis, and the prose must distinguish numerical findings from interpretation without exceeding the identification assumptions.

The final paper will use numbered sections, continuous prose, British English and the first person singular for my research choices and interpretations. It will retain a keywords section and attribute external facts, ideas and methods at the relevant claims. I will check the mathematical reasoning and any claimed contribution against the consulted literature. An auditable account of an imprecise or contrary result can satisfy these criteria; a preferred direction of the estimated response cannot substitute for them.
