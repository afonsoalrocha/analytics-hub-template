# Product contract — monthly commerce mart

## Question it answers

How did delivered orders, product revenue, and average ticket move in each complete purchase month?

## Grain

One row per `purchase_month`.

## Refresh

The automation `automations/monthly-close` appends newly closed months. A month that is already in the snapshot is frozen. The run validates the whole frame and then replaces the snapshot in one write.

## Columns

| Column | Status | Unit |
| --- | --- | --- |
| `purchase_month` | grain | month |
| `delivered_orders` | certified | orders |
| `product_revenue` | certified | BRL, freight excluded |
| `average_ticket` | certified | BRL, price plus freight per delivered order |

The indicative repurchase rate is a separate file, `repurchase_by_cohort.csv`, at the cohort grain. Its rate column is `repurchase_rate_indicative`.

## Filters

- `order_status = 'delivered'`
- The purchase month is closed and every calendar day of it is present in the source.

## What a certified answer carries

Period, filters, unit, and the time of the last load. Request 001 writes these in `outputs/publication.json`.

## What this product refuses

Visit-to-order conversion. The metric card is `blocked`. The column is absent.

## Consumers

The worked example request, and any review that reads the mart after the gates have passed. A warning is attached to the gate report and stays visible.
