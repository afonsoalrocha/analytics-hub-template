# Visit-to-order conversion

- id: `visit_to_order_conversion`
- status: `bloqueada`

> **Bloqueada.** This metric stays unpublished.

The Olist public dataset has no visit or session table. Publishing a conversion rate would invent the denominator. The metric stays blocked until a traffic source is connected and reconciled to orders.

## Definition

Delivered orders divided by visits. The public dataset has orders and no visits.

## Formula

- numerator: `count(distinct order_id)`
- denominator: `count of visits or sessions`
- aggregation: `ratio`

## Grain and time

- grain: `session_id, which this dataset does not contain`
- default date: `session_date`
- maturity: 0 days

## Required filters

- None.

## Allowed dimensions

- `purchase_month`: A monthly rate would still need a visit denominator for that same month.

## Reconciliation

A web-analytics property, reconciled to orders on a shared time window. None is connected in this template.

## Ownership

- owner: template maintainer
- decided at: 2026-11-10

## History

- 2026-11-10: Blocked at creation because the example dataset cannot support the question.
