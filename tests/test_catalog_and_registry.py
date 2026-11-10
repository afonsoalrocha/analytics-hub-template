from pathlib import Path

import yaml

from catalog import validate_catalog
from registry import validate_registry

ROOT = Path(__file__).resolve().parents[1]


def test_metric_catalog_matches_the_index_and_the_schema():
    assert validate_catalog(ROOT) == []


def test_registry_matches_the_demand_folder():
    assert validate_registry(ROOT) == []


def test_knowledge_topics_exist():
    index = yaml.safe_load((ROOT / "conhecimento" / "index.yaml").read_text(encoding="utf-8"))
    for topic in index["topics"]:
        assert (ROOT / topic["path"]).is_file()


def test_maturity_window_has_one_value():
    card = yaml.safe_load(
        (ROOT / "conhecimento" / "metricas" / "repurchase_rate.yaml").read_text(encoding="utf-8")
    )
    demand = yaml.safe_load(
        (ROOT / "demandas" / "001-conversao-e-receita-mensal" / "config.yaml").read_text(
            encoding="utf-8"
        )
    )
    project = yaml.safe_load((ROOT / "dbt" / "dbt_project.yml").read_text(encoding="utf-8"))
    assert card["maturity_days"] == 90
    assert demand["maturity_days"] == 90
    assert project["vars"]["repurchase_maturity_days"] == 90


def test_demand_readme_states_the_gate_thresholds():
    text = (ROOT / "demandas" / "001-conversao-e-receita-mensal" / "README.md").read_text(
        encoding="utf-8"
    )
    config = yaml.safe_load(
        (ROOT / "demandas" / "001-conversao-e-receita-mensal" / "config.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert config["variation_threshold"] == 0.5
    assert config["reconciliation_tolerance"] == 0.005
    assert "50%" in text
    assert "0.5%" in text
    for name in (
        "delivered_orders.md",
        "product_revenue.md",
        "average_ticket.md",
        "repurchase_rate.md",
        "visit_to_order_conversion.md",
    ):
        assert (ROOT / "conhecimento" / "metricas" / name).is_file()
        assert name in text
