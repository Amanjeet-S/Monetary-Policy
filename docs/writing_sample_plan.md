# Writing-sample development plan

## 1. Purpose and scope

I am developing an individual quantitative economics paper with a maximum of twenty pages. The research connects economic formulation, mathematical reasoning, econometric identification and inference, implementation, independent judgement and clear communication. I will check the final paper's page count and presentation before release.

My question is how unexpected ECB monetary tightening affects German durable relative to non-durable consumer-goods production. The [research design](research_design.md) develops the proposed response contrast. The [data audit](data_audit.md) and [source register](sources.md) establish the available evidence and consultation record. The primary specification and main estimates remain outstanding.

## 2. Economic argument and contribution

I will explain the economic problem and the intended contribution near the beginning of the paper. The principal comparison will be the response difference at one prespecified horizon, with a limited response path and a small robustness set. I will establish what this comparison adds to the closest published research on monetary transmission and production heterogeneity, and whether its assumptions and precision support a useful economic conclusion. If the literature already answers the proposed question, I will refine the contribution before fitting the primary specification.

The production indices measure production rather than household consumption. Exports, inventories and supply conditions can also affect them. I will distinguish the contrast identified under the maintained assumptions from explanations of particular mechanisms. I will develop a substantive project-specific argument and preserve null, contrary, sensitive and imprecise findings. Added research value concerns what the evidence teaches, rather than a preferred sign or significance result.

I will attribute established identification and estimation methods at the relevant claims. Any independent derivation will explain its motivation, assumptions, intermediate steps and use. A claimed original theorem or method requires a checked literature comparison and a valid proof; familiar mathematics presented in new notation does not establish novelty.

## 3. Evidence and design sequence

I will first reconcile the recorded 315 dated raw EA-MPD observations with the 312 retained derived events, review event exclusions and monthly aggregation, and establish the shock decomposition, sign and scale. Missing observations, months without retained events and measured zero surprises require distinct treatment. I will review the production and price classifications, units, seasonal adjustment and revisions. Before locking the design, I will check whether free sources provide a later suitable vintage and preserve any new retrieval separately from the unchanged snapshot.

The literature review must cover the economic mechanisms and closest empirical comparisons as well as shock identification, local projections and inference. Published peer-reviewed articles take priority. I will check for published successors to working papers, use supplements for a defined gap, and record the version and sections actually consulted. Existing authorised institutional or publisher access can support reading at no additional cost. Metadata or an abstract cannot stand in for a completed full-text methods review.

I will then record and commit the primary horizon, output formula, shock measure and normalisation, sample dates, lags, controls, missingness and exclusion rules, inference procedure and limited robustness set before inspecting main estimates. Later departures will be dated and explained, with exploratory analysis identified. A local specification record documents research sequence; its existence alone establishes neither external preregistration nor causal identification.

## 4. Estimation and verification

Python will construct the estimation sample and implement the analysis. I will derive and check the response contrast, preserving covariance between the two production responses. Selected coefficients and uncertainty calculations will be independently implemented in R on the same sample with the same transformations, scaling and conventions. Numerical agreement checks implementation; the identifying assumptions require their own assessment.

I will justify inference for persistent outcomes, serial dependence and overlapping horizons, distinguish uncertainty at the primary horizon from inference over a response path, and address influential observations and uncertainty in the supplied shocks where relevant. Sample losses will be recorded at each horizon. Robustness comparisons must state whether they change the sample, estimand or identifying assumptions. Shared policy shocks in additional geographical comparisons do not supply independent replications.

Independent critical review will challenge the economic interpretation, literature comparison, assumptions, mathematics, code and uncertainty calculations. I will check the supported domain, boundary cases and invalid inputs, retain unsuccessful checks, and resolve material disagreements before claiming completion. The final calculations, tables, figures and notebook must run from the retained inputs and declared environment, with the extent of each replay stated accurately.

## 5. Paper and repository presentation

The main paper will present the question, economic reasoning, identification, principal evidence and interpretation in connected research prose. Essential derivations will remain in the paper; longer proofs and verification details can be placed in supporting material within my twenty-page limit. The abstract will state the question, approach and principal finding concisely. Keywords will appear below it. I will use the established article layout, British English, first person singular for my decisions and interpretations, numbered sections, author–date citations and an alphabetised bibliography. Amanjeet Singh will appear on the author line and in the relevant file metadata.

Every table and figure must clarify a substantive claim and be referred to and interpreted in the text. I will choose between prose, tables and plots according to what communicates the evidence most clearly. Colour figures will have readable labels, units, legends and uncertainty descriptions, with legends clear of the plotted evidence. Two- or three-dimensional displays are appropriate only when they add information. Mathematical notation will follow conventional journal typesetting, and the final PDF will be visually checked for overflow and obscured content.

The repository will be self-contained, with a clear entry point, necessary source records, readable code and straightforward reproduction instructions. I will consolidate redundant notes and keep detailed execution records separate from the economic narrative. Research commits will describe meaningful completed changes and preserve their actual chronology. The final LaTeX source and matching PDF must represent the same verified version.

## 6. Completion

Completion requires a literature-grounded contribution, resolved or explicitly bounded source and event-coverage questions, a recorded primary specification, verified estimates and uncertainty, reproducible evidence and a paper whose conclusions follow from its assumptions and findings. The analysis must communicate what it teaches and why it matters. A data audit, elaborate presentation or large test count cannot substitute for that research argument.
