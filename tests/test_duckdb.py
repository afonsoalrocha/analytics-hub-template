from connectors.duckdb import DuckDBConnector


def test_query_and_healthcheck(tmp_path):
    database = tmp_path / "local.duckdb"
    with DuckDBConnector(str(database)) as connector:
        frame = connector.query("select 1 as ok")
        assert connector.healthcheck()
    assert frame["ok"].iloc[0] == 1
