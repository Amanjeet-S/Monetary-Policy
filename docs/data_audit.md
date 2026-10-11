# Data and shock-source audit

## 1. Current and retained vintages

The [10 October 2026 snapshot](../data/raw/2026-10-10/manifest.json) is the active source vintage. The [15 September snapshot](../data/raw/2026-09-15/manifest.json) remains unchanged. Both preserve downloaded bytes, attribution, units and SHA-256 hashes.

| Series | First | Last | Current rows |
| --- | --- | --- | ---: |
| Durable consumer-goods production | 1991-01 | 2026-08 | 428 |
| Non-durable consumer-goods production | 1991-01 | 2026-08 | 428 |
| Historical all-items HICP | 1996-01 | 2025-12 | 360 |
| Monthly policy/information contributions | 1999-01 | 2025-10 | 322 |
| Event contributions | 1999-01-07 | 2025-10-30 | 312 |

The production update adds August 2026 and revises July non-durable production from 92.3 to 91.4; the remaining overlapping observations are unchanged. The historical HICP request is unchanged. Eurostat now supplies a successor classification. For the primary analysis I retain the coherent historical series: every required lagged price observation precedes its endpoint, so later price coverage would add no primary observations. I do not splice classifications. The available shock vintage is unchanged. Common input coverage remains 322 months before lag and response-horizon losses.

Production is seasonally and calendar adjusted, 2021=100. Historical HICP is unadjusted, 2015=100. These are retrieved historical observations, rather than reconstructed real-time vintages. Under [Regulation 2020/1197, Annex II.A](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32020R1197), consumer durables comprise NACE Rev. 2 groups 26.4, 26.7, 27.5, 30.9, division 31, and groups 32.1 and 32.2. Division 29 motor vehicles is capital goods. [Eurostat's transition record](https://ec.europa.eu/eurostat/web/short-term-business-statistics/legislation) retains Rev. 2 through 2027. The two indices therefore cannot be equated with household durable/non-durable expenditure.

## 2. Reconciled construction

I checked the source update at commit `f7ffc821b0ade71dd38539e4044e25368dfb4dc1` against the raw EA-MPD workbook. Its 315 dated observations become exactly 312 after the implementation's explicit exclusions: 13 September 2001, 17 September 2001 and 8 October 2008, labelled joint Fed–ECB announcements in the source code. All six monthly fields reproduce event sums within recorded floating-point tolerances. Independent uncentred PCA and median-rotation calculations reproduce all supplied rounded factors and components.

The 322 months contain 277 months with retained events and 45 without. Six event factors are observed zeros; these can have offsetting nonzero median components and are distinct from empty-event months. No retained rate/equity inputs are missing after the exclusions. The update uses four OIS maturities and scales the factor to one-year OIS-surprise variation before division by 100. A 0.01 movement is one basis point in that normalised factor, not necessarily a one-basis-point policy-rate change.

The [review metadata](../data/metadata/shock_source_review_2026-10-10.json) records exact URLs, hashes, exclusions and source rights. The optional audit reproduces these checks from externally retained source files. Agreement establishes construction and coverage; identifying assumptions and the economic response still require separate analysis.

## 3. Primary-sample variation

The [descriptive summary](../results/sample_description.json) retains moments on the 308 primary origins, including 263 months with retained events and 45 without. Policy, information and recomposed factor standard deviations are 3.32, 2.79 and 4.35 basis points before controls, and 2.77, 2.41 and 3.59 after projecting each contribution on the same control matrix. These are descriptive factor units. The covariance ratio reproduces the recorded mixture weight; no outcome regression is fitted.
