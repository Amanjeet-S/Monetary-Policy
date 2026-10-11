# Recorded empirical results

## 1. Main comparison

I estimate a twelve-month policy-component response of −2.29 percentage log-change points in German durable relative to non-durable consumer-goods production, with a contextual 95 per cent pointwise interval of [−4.18, −0.40]. The undivided-surprise coefficient is −1.03 [−2.24, 0.17]. Every response uses a ten-basis-point increase in the supplied annualised near-term rate-factor contribution, rather than an equal change in an ECB policy rate.

The primary information-adjustment gap, the undivided coefficient less the policy coefficient, is +1.26. Its prespecified conservative 95 per cent product bounds are [−0.11, 3.31], so the declared conservative procedure does not reject the primary zero-gap hypothesis. The point estimate suggests a smaller relative contraction when information and policy are combined, but the interval permits both a negligible negative difference and a substantial positive difference. This is imprecision, rather than evidence of no adjustment effect. Non-rejection is specific to the declared procedure, not a conclusion about every valid test of the union null. The underlying sector point responses are −3.47 for durables and −1.18 for non-durables; their covariance is retained when estimating the difference.

## 2. Declared sensitivities

The table reports every declared twelve-month sensitivity. Policy intervals are contextual and pointwise; gap intervals are the conservative product bounds. Both bandwidth changes retain the primary coefficients.

| Specification | Observations | Policy contrast and 95 per cent interval | Undivided coefficient | Gap and conservative 95 per cent bounds |
| --- | ---: | --- | ---: | --- |
| Primary, twelve lags | 308 | −2.29 [−4.18, −0.40] | −1.03 | 1.26 [−0.11, 3.31] |
| Six lags, same origins | 308 | −2.52 [−4.62, −0.42] | −1.35 | 1.17 [−0.16, 3.13] |
| Poor-man decomposition | 308 | −2.27 [−4.06, −0.47] | −1.04 | 1.23 [−1.02, 4.19] |
| Pre-pandemic outcomes | 228 | −2.08 [−4.28, 0.11] | −1.42 | 0.66 [−1.44, 3.09] |
| Shorter HAC bandwidth | 308 | −2.29 [−4.16, −0.43] | −1.03 | 1.26 [−0.08, 3.27] |
| Longer HAC bandwidth | 308 | −2.29 [−4.25, −0.34] | −1.03 | 1.26 [−0.14, 3.36] |

Every gap point estimate is positive, but every conservative gap interval includes zero. The poor-man comparison is less precise and replaces both current and lagged components; six lags changes the conditioning set on matched dates. The pre-pandemic gap is smaller, its information coefficient changes sign to −0.62, and its policy-contrast interval also includes zero. The pre-pandemic undivided interval is [−2.66, −0.19]. These differing separate significance patterns are not tests of coefficient differences. The shorter sample also changes policy composition and the projection target, so I cannot attribute its change solely to the pandemic.

## 3. Omitted-variance illustration

Multiplying the component-difference standard error by the realised weight gives 0.6005 and an illustrative normal interval [0.08, 2.44]. The population calculation includes weight variation and cross covariance, giving 0.6749 and a regularity-dependent diagnostic interval [−0.06, 2.58]. Direct weight variation contributes about 5.0 per cent and the cross term 15.8 per cent of the estimated variance. Omitting those terms does not validate a conditional confidence interval or replace the locked product procedure. This post-estimation arithmetic applies established projection algebra without a new fitted model or preferred test.

## 4. Limits and verification

The common-sample path uses 296 origins. Its policy point estimates are negative and gap estimates positive throughout horizons zero to twenty-four, but its intervals are pointwise. Selected horizons cannot replace the primary result or establish simultaneous path significance. Horizon zero covers the whole announcement month, including pre-announcement production. The path's twelve-month gap is 1.21 [−0.20, 3.27], on a shorter sample than the primary estimate.

Single-origin deletions preserve the gap's point-estimate sign, but the largest change is 0.38, approximately thirty per cent of its original value, and pandemic dates feature among the most influential origins. Maximum leverage is 0.565. I retain these influence findings without automatic exclusions. The results are conditional on the supplied factor, rotation, vintage and specification; they do not propagate construction or identification-set uncertainty. Production responses do not separately identify household demand, exports, inventories or financing mechanisms, and durability heterogeneity is already established in the literature.

The specification was locked in commit `66ed69c136b41d2775a62909375a4d1cd00ec048` and implementation committed before fitting. Independent reconstruction in R 4.6.1 passed for nine selected cases and 351 numerical comparisons, covering transformations, samples, estimates, joint calendar covariance and intervals. The maximum absolute difference was approximately 1.04 × 10⁻¹³. This agreement checks calculation; it does not establish causal identification or independent empirical replication.

The [recorded estimates](../results/estimates.csv), [response path](../results/figures/response_paths.svg), [gap sensitivities](../results/figures/primary_sensitivity.svg) and [independent verification record](../results/verification.json) retain the numerical evidence.

## 5. Recorded supplementary inference

The [post-estimation record](gap_followup_specification.json) acknowledges that the estimates and preliminary diagnostic arithmetic were already known. The [complete follow-up](../results/gap_followup.json) retains all six cases. The primary intersection-union test gives p=0.036, while its covariance-aware joint-ellipse product bounds are [−0.19, 3.18]. The poor-man and earlier-period tests do not reject, with p=0.174 and 0.414, and every ellipse interval includes zero. This is supplementary nominal evidence for the selected decomposition; the original interval and construction, magnitude and causal uncertainty remain.
