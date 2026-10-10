# Initial data audit

## 1. Retained source coverage

Snapshot date: 15 September 2026. The files are public downloads, preserved unchanged with source URLs and SHA-256 checksums in the [manifest](../data/raw/2026-09-15/manifest.json).

| Series | First observation | Last observation | Rows |
| --- | --- | --- | ---: |
| German durable consumer-goods production | 1991-01 | 2026-07 | 427 |
| German non-durable consumer-goods production | 1991-01 | 2026-07 | 427 |
| German all-items HICP | 1996-01 | 2025-12 | 360 |
| ECB shocks, monthly | 1999-01 | 2025-10 | 322 |
| ECB shocks, events | 1999-01-07 | 2025-10-30 | 312 |

The three German index series have no missing observations inside these reported intervals. The monthly shock file has no duplicate year-month keys or blank numeric fields. The production and monthly shock series overlap for 322 months before lags, controls, exclusions and response-horizon losses.

Production uses seasonally and calendar adjusted volume indices, 2021=100. HICP uses the historical all-items classification and 2015=100. Source flags and observation dates remain in the original JSON. This is a current retrieval of historical observations, not an as-published historical vintage.

## 2. Limitations still to resolve

I will reconcile event exclusions and aggregation against the author's code and raw EA-MPD data. The inspected raw workbook had 315 dated rows per event-window sheet; the derived CSV contains 312 events. I will review shock normalisation, sign restrictions and decomposition before choosing the primary measure. Transformations, lags, controls and the primary horizon must be specified before estimation. I will review revisions and seasonal-adjustment conventions before interpreting historical comparisons, and evaluate influence and statistical precision. Row counts do not establish adequate power.

The separate raw ECB workbook is linked from the [source register](sources.md) and is not redistributed here. The audit script and notebook reproduce coverage from the included German index and derived shock files without relying on that workbook.
