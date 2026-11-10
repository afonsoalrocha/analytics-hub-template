import pytest

from connectors.base import ConnectorError
from connectors.policy import Policy, is_read_only_sql, load_policy


def test_read_verbs_and_a_single_statement_are_allowed():
    allowed = [
        "select 1 as ok",
        "SELECT created_at, updated_at FROM orders",
        "with src as (select 1 as ok) select * from src",
        "show tables",
        "describe orders",
        "explain select 1",
        "values (1)",
        "select 1;",
        "select 'drop table orders' as note",
        "SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = @project",
    ]
    for statement in allowed:
        assert is_read_only_sql(statement), statement


def test_writes_and_stacked_statements_are_refused():
    refused = [
        "delete from orders",
        "drop table orders",
        "insert into orders values (1)",
        "update orders set price = 1",
        "create table orders (id int)",
        "select 1; delete from orders",
        "with gone as (delete from orders) select 1",
        "",
    ]
    for statement in refused:
        assert not is_read_only_sql(statement), statement


def test_load_policy_defaults_and_overrides(monkeypatch):
    monkeypatch.delenv("CONNECTOR_DRY_RUN", raising=False)
    monkeypatch.delenv("CONNECTOR_ALLOW_WRITE", raising=False)
    monkeypatch.delenv("CONNECTOR_MAX_BYTES", raising=False)
    assert load_policy() == Policy(False, False, 1_073_741_824)
    monkeypatch.setenv("CONNECTOR_DRY_RUN", "true")
    monkeypatch.setenv("CONNECTOR_ALLOW_WRITE", "yes")
    monkeypatch.setenv("CONNECTOR_MAX_BYTES", "32")
    assert load_policy() == Policy(True, True, 32)


def test_load_policy_rejects_a_bad_flag(monkeypatch):
    monkeypatch.setenv("CONNECTOR_DRY_RUN", "maybe")
    with pytest.raises(ConnectorError, match="CONNECTOR_DRY_RUN"):
        load_policy()
