from datetime import date, timedelta

import pandas as pd

from gates.checks import check_anomalous_variation, complete_months, month_start
from synthetic_olist import build_frames


def test_seed_is_stable_and_tells_one_warning():
    first = build_frames(42)
    second = build_frames(42)
    pd.testing.assert_frame_equal(first["orders"], second["orders"])
    orders = first["orders"].copy()
    orders["day"] = pd.to_datetime(orders["order_purchase_timestamp"]).dt.date
    ready = complete_months(orders["day"])
    assert ready[0] == date(2017, 1, 1)
    assert ready[-1] == date(2018, 8, 1)
    assert date(2016, 12, 1) not in ready
    assert date(2018, 9, 1) not in ready
    expected_days = {
        date(2017, 1, 1) + timedelta(days=offset)
        for offset in range((date(2018, 8, 31) - date(2017, 1, 1)).days + 1)
    }
    assert expected_days.issubset(set(orders["day"]))

    delivered = orders.loc[orders["order_status"] == "delivered"].copy()
    delivered["purchase_month"] = delivered["day"].map(month_start)
    counts = (
        delivered.groupby("purchase_month", as_index=False)["order_id"]
        .nunique()
        .rename(columns={"order_id": "delivered_orders"})
    )
    counts = counts.loc[counts["purchase_month"].isin(ready)]
    variation = check_anomalous_variation(
        counts,
        column="delivered_orders",
        key="purchase_month",
        threshold=0.5,
    )
    assert variation.state == "warn"
    assert variation.message.count("moved") == 1
    assert "2017-11-01" in variation.message

    items = first["order_items"].merge(first["payments"], on="order_id")
    gap = (items["payment_value"] - items["price"] - items["freight_value"]).abs().max()
    assert gap < 0.001

    customers = first["customers"]
    people = delivered.merge(customers, on="customer_id")
    per_person = people.groupby("customer_unique_id").agg(
        first_day=("day", "min"),
        orders=("order_id", "nunique"),
    )
    cutoff = date(2018, 8, 31) - timedelta(days=90)
    mature = per_person.loc[per_person["first_day"] <= cutoff]
    assert len(mature) == 20
    assert (mature["orders"] >= 2).sum() == 10
    assert (mature["orders"] >= 2).mean() == 0.5
