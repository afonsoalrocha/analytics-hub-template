# Product contract — monthly commerce mart

## Question it answers

How did delivered orders, product revenue, and average ticket move in each complete purchase month?

## Grain

One row per `purchase_month`.

## Refresh

The automation `automacoes/fechamento-mensal` appends newly closed months. A month that is already in the snapshot is frozen. The run validates the whole frame and then replaces the snapshot in one write.

## Columns

| Column | Status | Unit |
| --- | --- | --- |
| `purchase_month` | grain | month |
| `delivered_orders` | certificada | orders |
| `product_revenue` | certificada | BRL, freight excluded |
| `average_ticket` | certificada | BRL, price plus freight per delivered order |

The indicative repurchase rate is a separate file, `repurchase_by_cohort.csv`, at the cohort grain. Its rate column is `repurchase_rate_indicativo`.

## Filters

- `order_status = 'delivered'`
- The purchase month is closed and every calendar day of it is present in the source.

## What a certified answer carries

Period, filters, unit, and the time of the last load. Demand 001 writes these in `outputs/publication.json`.

## What this product refuses

Visit-to-order conversion. The metric card is `bloqueada`. The column is absent.

## Consumers

The worked example demand, and any review that reads the mart after the gates have passed. A warning is attached to the gate report and stays visible.
