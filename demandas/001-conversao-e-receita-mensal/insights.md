# Insights — demand 001

## Recommendation

Use the certified monthly table for a review of delivered orders, product revenue, and average ticket. Quote the repurchase rate only with the word Indicativo and with the 90-day maturity window. Leave visit-to-order conversion out of the review until a traffic source exists.

## Context

The question asked for demand, revenue, ticket, repurchase, and visit conversion on the public Brazilian e-commerce extract published by Olist. The extract contains orders, items, customers, and payments from 2016 through 2018. It does not contain visits. The synthetic seed follows the same tables so the demand still runs when the download is unavailable.

Certified metrics use the purchase month and delivered status. The partial-month rule drops a month that is still open or that misses a day. Repurchase is indicative because the 90-day window is a template assumption. Conversion is blocked because the denominator would be invented.

## Findings

- The certified output is one row per complete purchase month. The period, the filters, the units, and the load time are in `outputs/publication.json` after `make demo`.
- On the public extract, early months and the tail are incomplete, so they stay out. The published window starts in February 2017 and ends in August 2018.
- The variation gate warns when delivered orders move by more than 50% versus the previous month. On this public extract the early-2017 ramp (into March and into May) and November 2017 cross that line. November is the sharp step. The synthetic seed is built so only November 2017 crosses it: that month has twice the daily orders of the months around it, and December returns to the base rate, which is a 48% decline and stays inside the threshold.
- Item value and payment value on the public extract sit well inside the 0.5% reconciliation tolerance for the published months. The synthetic seed matches to the cent, because each payment is price plus freight. A breach would be a warning in `outputs/gate_report.json`, and the certified revenue definition would still be item price.
- On the synthetic seed, 10 of 20 mature people order again. First purchases fall in December 2016 and January 2017, so the indicative file has a row per cohort. Ten people who first buy in July 2018 are inside the extract and outside the 90-day window, and they stay out of the rate. The public extract produces its own cohorts. Read the indicative file, and keep the suffix.
- Visit-to-order conversion has no column in either output file.

## Recommendations

- Brief the monthly review from `outputs/monthly_commerce.csv`.
- When a variation warning fires, say which month moved and whether the movement is a real change in demand. The warning is the question, and the certified number remains the number.
- Keep repurchase in the appendix with the Indicativo label until a human replaces the 90-day window with a decided definition and moves the card to `certificada`.
- Connect a traffic source before anyone asks again for a conversion rate. Until then the blocked card is the answer.

## Files

- `dbt/models/marts/mart_monthly_commerce.sql`
- `dbt/models/marts/mart_repurchase_by_cohort.sql`
- `dbt/models/audit/audit_monthly_reconciliation.sql`
- `outputs/monthly_commerce.csv`
- `outputs/repurchase_by_cohort.csv`
- `outputs/publication.json`
- `outputs/gate_report.json`
- `automacoes/fechamento-mensal/snapshots/monthly_commerce.csv`
- `conhecimento/metricas/`

## Revision log

Append-only. Add a new entry. Leave the earlier entries as they were written.

### 2026-11-10 — First reading

The months that move by more than 50% looked, on a first pass, like a failed close. That reading treated an anomaly signal as an integrity failure.

### 2026-11-10 — A warning stays a warning

The acceptance rules already separate the two. A partial month, a broken grain, a missing denominator, or a blocked metric stops the write. A large month-to-month move is recorded and the certified table is still published. The definitions were left as written. The gate report lists the months that moved on the run you just made.
