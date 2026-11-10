# Average ticket

- id: `average_ticket`
- status: `certificada`

## Definition

Item price plus freight, divided by delivered orders, in the month of the purchase.

## Formula

- numerator: `sum(price) + sum(freight_value)`
- denominator: `count(distinct order_id)`
- aggregation: `ratio`

## Grain and time

- grain: `delivered order rolled up to purchase_month`
- default date: `order_purchase_timestamp`
- maturity: 0 days

## Required filters

- `order_status = 'delivered'`
- `complete calendar months only`

## Allowed dimensions

- `purchase_month`: No extra caution.
- `customer_state`: A state with a handful of orders can swing the ticket. Publish the order count beside any state cut.

## Reconciliation

The numerator is the item GMV that the reconciliation gate compares with payment_value. The denominator is delivered_orders.

## Ownership

- owner: template maintainer
- decided at: 2026-11-10

## History

- 2026-11-10: Initial definition for the public Olist example. Ticket includes freight; product revenue does not.
