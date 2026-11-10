# Architecture — monthly close

The monthly close publishes `mart_monthly_commerce` in append mode. A month that has already been written stays as it was.

## Metric definitions

The mart carries three certified metrics. The cards are the source of truth:

- [Delivered orders](../../../knowledge/metrics/delivered_orders.md)
- [Product revenue](../../../knowledge/metrics/product_revenue.md)
- [Average ticket](../../../knowledge/metrics/average_ticket.md)

Repurchase is indicative and is published by the request, not by this snapshot. Visit-to-order conversion is blocked and has no column.

## Grain

One row per `purchase_month`, the calendar month of `order_purchase_timestamp`.

## Sources

- `raw.orders`, `raw.order_items`, loaded by `scripts/prepare_data.py`
- `staging.stg_orders`, `staging.stg_order_items`
- `intermediate.int_complete_months`
- `marts.mart_monthly_commerce`

The public path is the Olist CSV sample. The offline path is the seeded synthetic extract. Both land in the same raw tables.

## Invariants

- A published month is closed, and the source has an order on every day of it.
- Delivered orders, product revenue, and average ticket are present and non-negative.
- A month already present in `snapshots/monthly_commerce.csv` keeps its values on the next run.
- The snapshot file is replaced only after the gates have passed. A block leaves the previous file in place.
- Zero language-model calls at runtime. The close reads the mart, runs the gates, and writes the snapshot.

## Gates

| Gate | Severity | What it checks here |
| --- | --- | --- |
| Grain uniqueness | block | one row per purchase month |
| Value domain | block | counts and amounts are present and non-negative |
| Partial month | block | the mart contains no open or incomplete month |
| Temporal coverage | block | every day of each published month exists in the source |
| Frozen history | block | an existing snapshot month is unchanged |

The request runner also checks reconciliation (warn) and anomalous variation (warn) before the first publication. This automation repeats the integrity gates on every later close.

## Decisions

### 2026-11-10 — Purchase month, not delivery month

What: The clock is `order_purchase_timestamp`, truncated to the month.
Why: The question is about request that was placed. Delivery timestamps are empty for orders that have not arrived, so they are a poor clock for a complete-month series. Delivered status is a filter.
Who: Human analyst (template maintainer).

### 2026-11-10 — Complete months only

What: A month is published when every calendar day has at least one source order and the month has ended inside the extract.
Why: An open month looks like a collapse when it is compared with a full month. A missing day is left unpublished rather than filled with zero.
Who: Human analyst (template maintainer).

### 2026-11-10 — Item price is certified revenue; payments reconcile it

What: Product revenue sums `price` on delivered orders and excludes freight. Average ticket uses price plus freight. `payment_value` is the independent source, with a 0.5% warning tolerance declared on the request.
Why: Freight is a logistics amount. Payments usually sit near price plus freight, and they are a check rather than the definition.
Who: Human analyst (template maintainer).

### 2026-11-10 — History is frozen in append mode

What: The second and later runs may add months. They may not change a month that is already in the snapshot.
Why: A monthly review that restates last month without a trace undermines the previous briefing. A correction is a new decision, recorded in this file, and a deliberate rebuild of the snapshot.
Who: Human analyst (template maintainer).

### 2026-11-10 — Repurchase stays indicative and conversion stays blocked

What: This snapshot has neither column. Repurchase is written by the request with the `_indicative` suffix. Conversion is documented on its card and omitted.
Why: The 90-day window is a template assumption. The dataset has no visits, so a conversion rate would invent a denominator.
Who: Human analyst (template maintainer).

## Out of scope

- Rebuilding history in place. Replace the snapshot on purpose, and record why, when a certified definition changes.
- Seller scorecards, freight subsidies, and state rankings.
- Credentials for a remote warehouse. The example runs in local DuckDB.

## Next steps

- Point `source_relation` at the same mart in a remote warehouse only through a connector configured from the environment.
- When a human certifies repurchase, give it a snapshot of its own and keep the revision on the metric card.
