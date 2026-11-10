# Product revenue

- id: `product_revenue`
- status: `certificada`

## Definition

Sum of item price for delivered orders, in the month of the purchase. Freight is excluded.

## Formula

- numerator: `sum(price)`
- denominator: `none`
- aggregation: `sum`

## Grain and time

- grain: `order item rolled up to purchase_month`
- default date: `order_purchase_timestamp`
- maturity: 0 days

## Required filters

- `order_status = 'delivered'`
- `complete calendar months only`

## Allowed dimensions

- `purchase_month`: No extra caution.
- `customer_state`: State cuts get thin quickly. Rank a state only when the order count is large enough for the decision in front of you.

## Reconciliation

Sum of payment_value on the same delivered orders. Payments are the independent source. They are expected to sit close to price plus freight, which is a different total from product revenue on purpose.

## Ownership

- owner: template maintainer
- decided at: 2026-11-10

## History

- 2026-11-10: Initial definition for the public Olist example. Freight stays out of product revenue.
