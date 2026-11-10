# 2018-08-20 — Freight share of the ticket

## Question

In the latest complete month, how much of (item price + freight) is freight?

## Query

`verificacoes-rapidas/2018-08-20-participacao-do-frete/check.py`

The script reads `audit.audit_monthly_reconciliation` in the local DuckDB warehouse and prints the latest complete month.

## Result

The number depends on the extract, so it is printed by the script rather than copied here. Run it after `make demo`.

## Conclusion

Freight belongs with the ticket; this check does not become a demand.

## Becomes a demand?

No. Average ticket already includes freight, and product revenue already excludes it. The check confirms the split is visible. It does not change a decision.
