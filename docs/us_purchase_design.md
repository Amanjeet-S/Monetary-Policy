# Household purchases after monetary tightening

## 1. Economic question

I ask whether real durable purchases recover their initial shortfall within three years of a monetary tightening. A purchase rate returning to its previous path does not repay purchases missed earlier. Recovery of cumulative purchases requires a subsequent excess over the no-shock path. This distinction follows from the durable-stock accounting identity and established durable-demand research; I do not present it as a new theory.

The US setting provides direct household purchase measures, a longer published narrative policy record and the central bank's pre-decision forecasts. I selected it before estimating US spending responses. The German announcement and future-policy studies remain retained in version history and their recorded results have not been altered.

## 2. Measurement and identification

I use the original [Romer and Romer (2004)](https://doi.org/10.1257/0002828042002651) workbook, obtained from its authors' university page and matched to the published source-purge regression. It contains 263 complete decision records from March 1969 to December 1996. I begin the common analytical sample in January 1971, retaining 238 events, so that the twelve-month baseline policy history and the twenty-four-month comparison both use observed monthly intentions. Pre-coverage zeros are not policy observations.

The treatment is an innovation in intended funds-rate policy, reported per 25 basis points. It includes the ensuing policy response and may reflect intended gradual implementation. A causal interpretation requires the pre-decision staff forecasts and predetermined state controls to capture policy-correlated information, together with the stated dynamic response restrictions. Residual orthogonality alone does not establish these assumptions. Each decision retains its own pre-meeting forecast inputs, avoiding conditioning an earlier decision on a later meeting's forecasts.

The monthly [BEA durable](https://fred.stlouisfed.org/series/DDURRA3M086SBEA), [nondurable](https://fred.stlouisfed.org/series/DNDGRA3M086SBEA) and [services](https://fred.stlouisfed.org/series/DSERRA3M086SBEA) chain quantity indexes measure real purchase flows. Dividing each category by its own preceding-month level cancels the reference-year dollar anchor and annual-rate conversion. I do not sum non-additive category chains. PCE includes purchases on behalf of resident persons, nonprofit institutions and imputations; it is not exclusively cash expenditure. Measurement follows the [BEA NIPA Handbook, chapter 5](https://www.bea.gov/resources/methodologies/nipa-handbook/pdf/chapter-05.pdf), December 2024, pp. 5-2–5-6.

My primary outcome sums the next 36 full monthly real purchase flows, divided by the last full pre-decision month's flow. Its coefficient is expressed in months of that baseline flow. The first twelve months and subsequent twenty-four months form exact, jointly estimated components. Subtracting the horizon length is a units normalisation, not a flat counterfactual assumption. A three-year shortfall is not a lifetime loss or a directly measured durable-service response.

## 3. Estimation and checks

The [prospective specification](us_purchase_specification.json) fixes outcomes, common rows, controls, inference and sensitivities before the first US spending fit. All current source-purge predictors enter the response regression. Established partial-regression algebra then makes the matched result invariant to the estimated current purge coefficients; source measurement and information sufficiency remain separate concerns.

I sum same-month decision scores before applying a Bartlett calendar covariance estimator, retaining actual distances across months without meetings. The single primary endpoint has a 95 per cent interval. Declared endpoint and profile families receive multiplicity adjustment. Policy-history lengths, dependence bandwidths, leverage, the reserves-targeting regime and the partial decision month are examined as declared comparisons. Non-rejection is not evidence of complete recovery.

The separately observed [daily effective funds rate](https://fred.stlouisfed.org/series/DFF) provides an implementation check. Its fixed seven-day post-decision mean is compared with the seven-day pre-decision mean, excluding the decision day. Published repeated non-trading-day quotes are retained. The historical rate convention changed in 1973; current transaction-median methodology began in 2016, outside the estimation period. A supplementary rate-scaled ratio uses joint weak-scale inference and does not identify an intervention on the observed quotation.

## 4. Source versions

The original AER final reprint, Sections I.A–I.C, pp. 1057–1066, and its two-page data descriptions were consulted. The author's source workbook is retained unchanged, with its source authorship intact. No later narrative extension is spliced into the primary series. Macroeconomic data are the 11 October 2026 vintage and are not described as policymakers' real-time observations. Exact original and compressed-byte hashes appear in the [snapshot manifest](../data/raw/2026-10-11-us-purchases/manifest.json). Published paper texts remain outside the repository.
