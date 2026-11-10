# Delivered orders

- id: `delivered_orders`
- status: `certificada`

## Definition

Distinct orders with status delivered, counted in the month of the purchase.

## Formula

- numerator: `count(distinct order_id)`
- denominator: `none`
- aggregation: `count_distinct`

## Grain and time

- grain: `order_id rolled up to purchase_month`
- default date: `order_purchase_timestamp`
- maturity: 0 days

## Required filters

- `order_status = 'delivered'`
- `complete calendar months only`

## Allowed dimensions

- `purchase_month`: No extra caution.
- `customer_state`: State cuts get thin quickly. Rank a state only when the order count is large enough for the decision in front of you.

## Reconciliation

Distinct delivered order ids in staging.stg_orders for the same complete months.

## Ownership

- owner: template maintainer
- decided at: 2026-11-10

## History

- 2026-11-10: Initial definition for the public Olist example.
