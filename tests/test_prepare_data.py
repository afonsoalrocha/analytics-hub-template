import json

from prepare_data import prepare


def test_synthetic_load_creates_raw_tables(tmp_path):
    database = tmp_path / "warehouse.duckdb"
    origin = prepare("synthetic", database, tmp_path / "raw")
    assert origin == "synthetic"
    payload = json.loads((tmp_path / "origin.json").read_text(encoding="utf-8"))
    assert payload["origin"] == "synthetic"
    import duckdb

    connection = duckdb.connect(str(database))
    try:
        count = connection.execute("select count(*) from raw.orders").fetchone()[0]
        items = connection.execute("select count(*) from raw.order_items").fetchone()[0]
    finally:
        connection.close()
    assert count > 100
    assert items == count - 1
