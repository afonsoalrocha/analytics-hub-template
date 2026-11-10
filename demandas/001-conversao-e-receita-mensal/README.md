# 001 — Monthly delivered demand, revenue, and the conversion question

## Question

How did delivered demand and product revenue move from month to month, what was the average ticket, how many mature customers came back, and what share of visits became orders?

## Requester

Analytics lead. In a real workspace, replace this role with the person who asked.

## Decision this supports

Whether the monthly commerce table is fit to brief a monthly review, and which parts of the question this dataset can answer.

## Metrics

- [Delivered orders](../../conhecimento/metricas/delivered_orders.md) — `certificada`
- [Product revenue](../../conhecimento/metricas/product_revenue.md) — `certificada`
- [Average ticket](../../conhecimento/metricas/average_ticket.md) — `certificada`
- [Repurchase rate](../../conhecimento/metricas/repurchase_rate.md) — `indicativa`
- [Visit-to-order conversion](../../conhecimento/metricas/visit_to_order_conversion.md) — `bloqueada`

The machine-readable parameters for the gates live in [`config.yaml`](config.yaml).

## Grain

`purchase_month` for the certified table: the calendar month of `order_purchase_timestamp`.

`cohort_month` for repurchase: the calendar month of a person's first delivered purchase.

## Period

Complete calendar months inside the extract. A month is complete when the source has at least one order on every day of that month and the month has ended inside the extract. On the public Olist sample that window is February 2017 through August 2018. On the synthetic seed it is January 2017 through August 2018. Open and incomplete months stay out of the output.

## Out of scope

- Visit-to-order conversion. The dataset has no visit table, so the metric stays blocked.
- Freight as its own certified metric. Freight is part of the average ticket and of the reconciliation total.
- A forecast, a seller score, or a state ranking.
- Any figure from a private warehouse. This demand runs on the public Olist extract or on the synthetic seed.

## Acceptance criteria

Block:

- The grain `purchase_month` is unique.
- Every published month has a source order on every calendar day.
- Every closed, fully covered month is present. A missing month is left out. It is not published as zero.
- Every delivered order in a published month has at least one item.
- Counts and amounts are present and non-negative, and a month with zero delivered orders is not published.
- The repurchase rate sits between 0 and 1.
- Open or incomplete months are absent.
- `visit_to_order_conversion` is absent. `repurchase_rate_indicativo` keeps the suffix.
- The publication records the period, the filters, the unit of each certified metric, and the load time.
- A later close does not change a month that was already written to the monthly snapshot.

Warn:

- Item value (`price + freight`) and `payment_value` differ by more than 0.5% in a month.
- Delivered orders move by more than 50% versus the previous published month.

A warn is part of the review. It does not stop the publication. A block does.

## Status

`fechada`. The transitions are in [`../registro.yaml`](../registro.yaml). The reading of the result is in [`insights.md`](insights.md).

Run this demand with `make demo` from the repository root.
