# Data and measurement

## 1. Retained sources

The [11 October 2026 snapshot](raw/2026-10-11-us-purchases/manifest.json) retains unchanged original Romer–Romer policy data and compressed original official CSV bytes. Gzip is lossless; the manifest records compressed and original SHA-256 hashes. Downloaded source observations have not been overwritten. Article texts remain outside the repository.

| Series | Measurement |
| --- | --- |
| DDURRA3M086SBEA | Monthly real consumer-durable purchase quantity, 2017=100, seasonally adjusted |
| DNDGRA3M086SBEA | Monthly real nondurable purchase quantity, same units |
| DSERRA3M086SBEA | Monthly real services quantity, same units |
| DSPIC96 | Real disposable personal income, chained 2017 dollars, annualised and seasonally adjusted |
| PCEPI | PCE chain price index, 2017=100, seasonally adjusted |
| FEDFUNDS | Monthly effective funds-rate average, annual percentage points |
| DFF | Published daily effective funds-rate quotes, annual percentage points |

The original policy workbook supplies intended funds-rate changes, staff forecasts and revisions. It has 263 complete source-purge decisions; 238 decisions in January 1971–December 1996 enter the common analytical sample. Missing purges and pre-1969 monthly placeholders are not observed zero shocks.

## 2. Construction

`build_us_purchase_panel.py` verifies source hashes, reproduces the original purge and writes ignored processed monthly and event files. The [source audit](../results/us_source_audit.json) records coverage and replay precision. Policy histories use observed raw intentions. Each event keeps its own pre-decision forecasts.

Cumulative purchases sum months 1–36 after the decision month, divided by the last complete pre-decision month's quantity. Units are months of that category's baseline real purchase flow. Reference-year anchors and annual-rate factors cancel. Categories are compared separately; non-additive chained levels are not summed into a total. The timing sensitivity instead uses offsets 0–35 with the same pre-month denominator.

The fixed financial check compares seven published calendar-day rate quotes after a decision with seven before it, excluding the decision day. Repeated non-trading-day quotes enter unchanged. Observation dates are distinct from publication dates; historical rate methods changed in 1973. This implementation measure is not an exogenous rate intervention.
