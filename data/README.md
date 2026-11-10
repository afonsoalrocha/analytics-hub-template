# Data directory

This directory is created by `make demo`. Its contents are gitignored, apart from this note.

`scripts/prepare_data.py` writes:

- `raw/` — Olist CSV sample, when the download succeeds
- `warehouse.duckdb` — local DuckDB database used by dbt
- `origin.json` — `olist` or `synthetic`, so the publication can say which extract it used

The Brazilian E-Commerce Public Dataset by Olist is published on Kaggle
(<https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce>) under
CC BY-NC-SA 4.0. This template does not redistribute those files. The
download script fetches the CSV sample from the public repository
<https://github.com/olist/work-at-olist-data> (`datasets/`), and only the
four tables the example uses: orders, items, customers, and payments.
Geolocation is left behind because the example does not need it and the
file is large.

Attribute Olist when you publish a number from that extract, and keep the
CC BY-NC-SA 4.0 terms in mind. The synthetic seed is original to this
template and is what continuous integration builds.
