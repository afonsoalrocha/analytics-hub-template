PYTHON ?= python3
export DUCKDB_PATH := $(CURDIR)/data/warehouse.duckdb
export DBT_PROFILES_DIR := $(CURDIR)/dbt
export PYTHONPATH := $(CURDIR)/scripts

.PHONY: help setup data demo demo-synthetic demo-olist dbt-build publish verify test lint sqlfluff leak-scan render ci

help:
	@echo "make demo              Download the Olist sample, or fall back to the synthetic seed, and close demand 001."
	@echo "make demo-synthetic    Same path, forced offline."
	@echo "make demo-olist        Same path, download required."
	@echo "make test              pytest"
	@echo "make ci                lint, tests, dbt build, leak scan"

setup:
	$(PYTHON) -m pip install -r requirements.txt

data:
	$(PYTHON) scripts/prepare_data.py --mode auto

dbt-build:
	mkdir -p data
	dbt build --project-dir dbt --profiles-dir dbt

publish:
	$(PYTHON) scripts/run_demand.py
	$(PYTHON) automacoes/fechamento-mensal/run.py

verify:
	$(PYTHON) verificacoes-rapidas/2018-08-20-participacao-do-frete/check.py
	$(PYTHON) scripts/render_metrics.py --check
	$(PYTHON) scripts/render_skills.py --check
	$(PYTHON) scripts/validate_structure.py

demo: data dbt-build publish verify

demo-synthetic:
	$(PYTHON) scripts/prepare_data.py --mode synthetic
	$(MAKE) dbt-build publish verify

demo-olist:
	$(PYTHON) scripts/prepare_data.py --mode olist
	$(MAKE) dbt-build publish verify

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .
	$(PYTHON) scripts/render_skills.py --check
	$(PYTHON) scripts/render_metrics.py --check
	$(PYTHON) scripts/validate_structure.py

sqlfluff:
	mkdir -p data
	$(PYTHON) -m sqlfluff lint dbt/models dbt/tests

leak-scan:
	$(PYTHON) scripts/gates/leak_scan.py

render:
	$(PYTHON) scripts/render_metrics.py

ci: lint sqlfluff test
	$(PYTHON) scripts/prepare_data.py --mode synthetic
	$(MAKE) dbt-build publish verify
	$(MAKE) leak-scan
