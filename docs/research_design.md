# Research design

## 1. Economic question and contribution

I ask whether the apparent relative response of German consumer-goods production to an ECB rate surprise changes when policy and information components are estimated separately. Sectoral durability heterogeneity is established in Peersman and Smets (2005), Dedola and Lippi (2005), Durante, Ferrando and Vermeulen (2022) and Choi, Willems and Yoo (2024). The particularly close, unpublished Flaccadoro and Ropele (2026) also uses consumer-goods production, information-adjusted shocks and local projections. The [source register](sources.md) distinguishes their outcomes, classifications and consulted versions. A German label or a newer vintage is insufficient for originality; the intended contribution is a matched economic reassessment of information adjustment with a transparent decomposition and joint uncertainty.

The design is not locked and no main response estimates have been inspected. Twelve months remains the proposed primary horizon. I will record the outcome transformation, controls, lag order, sample, shock scale, inference and limited robustness set before estimation.

## 2. Measurement and identification

The official consumer-durable production grouping excludes motor-vehicle manufacturing, which belongs to capital goods. It also differs from household purchases and coarse two-digit industry groupings. The [data audit](data_audit.md) records classifications, vintages, exclusions and shock construction. Production can respond through exports, inventories and financing as well as domestic demand.

The proposed monetary-policy and information measures are the supplied median-rotation contributions, in common annualised percentage-point units. Their sum reconstructs the near-term rate factor. The update differs from the original Jarociński and Karadi (2020) implementation, and its sign restrictions do not establish exogeneity by themselves. A causal interpretation requires usable announcement-window identification and conditional orthogonality to other production determinants. Bauer and Swanson (2023a) provides a published challenge to interpreting co-movement as proof of private information. I will include both contemporaneous components, justify predetermined controls and state the dependence of inference on the adopted shock construction.

## 3. Matched estimands

For positive production indices $D$ and $N$, my candidate cumulative outcome is

$$
Y_{t,h}=100\{\log(D_{t+h}/N_{t+h})-\log(D_{t-1}/N_{t-1})\}.\tag{1}
$$

It measures a difference in cumulative percentage log changes; constant index rebasing cancels. On identical observations and controls $Z$, I compare a projection on policy contribution $m$ and information contribution $c$ with one on their recomposed sum $r=m+c$. The policy coefficient is $\beta_{m,h}$, the information coefficient $\beta_{c,h}$, and the undivided-surprise coefficient $\gamma_h$. The information-adjustment gap is $\delta_h=\gamma_h-\beta_{m,h}$; all response coefficients are percentage log-change points per common declared shock unit. It is a different estimand from the policy response itself.

Established partial-regression algebra, reviewed in Ding (2021), gives the exact sample identity

$$
\widehat\delta_h=\widehat w_{c,h}(\widehat\beta_{c,h}-\widehat\beta_{m,h}),
\qquad
\widehat w_{c,h}=\frac{r'M_Zc}{r'M_Zr},\quad
M_Z=I-Z(Z'Z)^{-1}Z'.\tag{2}
$$

This requires common rows, controls and scaling. The control matrix includes an intercept and has full column rank; the residualised two-component design has full rank, positive residual degrees of freedom and nonzero residualised rate variation. The weights need not lie between zero and one. Source-sample orthogonality does not survive automatically after monthly aggregation, control residualisation or horizon trimming. The identity is established projection mathematics, not a new theorem; its economic use is to distinguish component-response differences from the mixture of policy and information news.

## 4. Inference and verification

For population projection coefficients, the estimated mixture weight varies with the sample. I will preserve the joint scores, actual residuals and cross-model score covariance of both regressions, including the covariance between $\widehat\beta_{m,h}$ and $\widehat\delta_h$. Multiplying the component-difference standard error by a fixed sample weight generally omits weight variation under alternatives; if the population weight is zero but the component responses differ, weight variation leads the gap's uncertainty. Product-Wald inference can become nonregular when both the population weight $w_{c,h}$ and component-response difference $\theta_h=\beta_{c,h}-\beta_{m,h}$ vanish; a prespecified projection of a valid joint region for $(w_{c,h},\theta_h)$ is a conservative alternative. Full derivations and boundary cases belong in the paper's appendix.

The covariance procedure requires appropriate moment, dependence and rank conditions. Lagged growth controls do not automatically inherit Montiel Olea and Plagborg-Møller's (2021) lag-augmentation theorem; the procedure must reflect the consulted 2026 author corrigendum. HAC bandwidth, finite-sample conventions and calendar alignment require explicit choices. A primary-horizon interval is pointwise; intervals along a response path require separate labelling or valid joint inference. The supplied factor and rotation are not an IV first stage, and ordinary regression uncertainty does not incorporate their construction or identification uncertainty.

Python will implement the analysis, with selected coefficients and uncertainty independently checked in R on the same sample. I will retain influence, sample-loss and supported-domain checks, plus a small declared sensitivity set. Refining the study must improve its economic evidence, rather than select a desired significance result.

## 5. Paper and completion

The English paper will address this core monetary-economics question in at most twenty pages, including appendices and bibliographical references. The main text will present the essential setup, key propositions, empirical findings and economic intuition. Long derivations, proofs and specification deviations will be in appendices; footnotes will carry relevant asides. Equations will be numbered. Keywords below the abstract will span the full text line; proposed JEL codes are C22, E32 and E52, following the [AEA classification](https://www.aeaweb.org/econlit/jelCodes.php?view=econlit).

I will use British English, first person singular for my choices and interpretations, numbered sections, author–date citations and an alphabetised bibliography. Every colour figure or table must support and be discussed in the argument. Completion requires a literature-grounded contribution, a recorded primary specification, verified estimates, reproducible evidence and a visually checked LaTeX/PDF pair. Analytical reasoning, articulation, organisation and visual presentation must remain clear without sacrificing necessary detail.
