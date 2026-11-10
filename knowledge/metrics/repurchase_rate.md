# Repurchase rate

- id: `repurchase_rate`
- status: `indicative`

> **Indicative.** Publish this figure with the `_indicative` suffix and with its maturity window.

## Definition

People with two or more delivered orders, divided by people with at least one delivered order, among people whose first purchase is old enough to have had a chance to return.

## Formula

- numerator: `count of customer_unique_id with 2 or more delivered orders`
- denominator: `count of mature customer_unique_id`
- aggregation: `ratio`

## Grain and time

- grain: `customer_unique_id rolled up to the month of first purchase`
- default date: `order_purchase_timestamp`
- maturity: 90 days

## Required filters

- `order_status = 'delivered'`
- `first purchase at least maturity_days before the end of the last complete month`

## Allowed dimensions

- `cohort_month`: A cohort near the maturity cutoff has had little time to return. Read the window before comparing cohorts.

## Reconciliation

Count of mature people and count of people with two or more orders in mart_repurchase_by_cohort. There is no second customer system in this dataset.

## Ownership

- owner: template maintainer
- decided at: 2026-11-10

## History

- 2026-11-10: Initial indicative definition. The 90-day window is a template assumption and the column keeps the _indicative suffix.
