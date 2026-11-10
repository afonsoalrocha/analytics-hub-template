# Data directory

This directory is created by `make demo`. Its contents are gitignored, apart from this note.

`scripts/prepare_data.py` writes:

- `raw/` — Olist CSV sample, when the download succeeds
- `warehouse.duckdb` — local DuckDB database used by dbt
- `origin.json` — `olist` or `synthetic`, so the publication can say which extract it used

The Brazilian E-Commerce Public Dataset by Olist is published on Kaggle
(<https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce>) under
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
NonCommercial means the dataset is not for commercial use. ShareAlike
means an adaptation of the dataset stays under the same license. This
template does not redistribute those files. The MIT license of the
template code is a separate license and does not cover the CSVs.

The download script fetches the CSV sample from
<https://github.com/olist/work-at-olist-data> (`datasets/`). That
repository declares MIT on GitHub and is used only as the file source.
Treat the CSVs under the canonical Kaggle license, CC BY-NC-SA 4.0, which
is the more restrictive license and excludes commercial use. The script
keeps four tables: orders, items, customers, and payments. Geolocation is
left behind because the example does not need it and the file is large.

Attribute Olist when you publish a number from that extract. The synthetic
seed is original to this template and is what continuous integration builds.

Warehouse files, raw extracts, demand outputs, automation snapshots, and
logs are heavy artifacts. They stay out of git. The logic that produces
them — SQL, Python, YAML, and Markdown — stays in git.
