# Metric maturity ladder

A metric is readable only after the events that make it up have had time to happen. That wait is the maturity window. It is a property of the behavior, and it gets longer as you move down a funnel.

| Stage | What you are counting | How soon it can be read |
| --- | --- | --- |
| Visit or session | Traffic that may never buy | As soon as the day closes |
| Order | A purchase placed | When the day or month of the purchase has closed |
| Delivery | An order that reached the customer | After the delivery lag |
| Repurchase or return | A second action by the same person | After a window long enough for that second action |

The top of the funnel is fast. The bottom is slow. Publishing a bottom-of-funnel rate on people who have just arrived treats "not yet" as "never".

In this template the ladder shows up in three places:

- Delivered orders, product revenue, and average ticket use the purchase month and wait until that month is closed and every day of it is present in the source. Their card says `maturity_days: 0` because the partial-month gate, rather than an extra lag, keeps the open month out.
- Repurchase rate waits 90 days after a person's first purchase. The number is indicative. The column is `repurchase_rate_indicative`.
- Visit-to-order conversion would sit at the top of the funnel and would mature quickly, but this dataset has no visits. The card is `blocked` and the output omits it.

Replace the 90 days when a real definition is decided. Record the change in the metric card history. Leave the previous line in place.
