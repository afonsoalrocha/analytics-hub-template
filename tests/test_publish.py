import pandas as pd

from publish import plan_append


def _frame(months: list[str], orders: list[int]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "purchase_month": months,
            "delivered_orders": orders,
            "product_revenue": [order * 10 for order in orders],
            "average_ticket": [10.0 for _ in orders],
        }
    )


def test_append_keeps_history_and_adds_a_new_month():
    previous = _frame(["2017-01-01", "2017-02-01"], [10, 12])
    current = _frame(["2017-01-01", "2017-02-01", "2017-03-01"], [10, 12, 11])
    plan = plan_append(
        current,
        previous,
        key="purchase_month",
        columns=["delivered_orders", "product_revenue", "average_ticket"],
    )
    assert plan.write
    assert plan.frame is not None
    assert plan.frame["purchase_month"].tolist() == ["2017-01-01", "2017-02-01", "2017-03-01"]
    assert plan.frame["delivered_orders"].tolist() == [10, 12, 11]


def test_append_refuses_to_rewrite_a_closed_month():
    previous = _frame(["2017-01-01"], [10])
    current = _frame(["2017-01-01", "2017-02-01"], [99, 12])
    plan = plan_append(
        current,
        previous,
        key="purchase_month",
        columns=["delivered_orders", "product_revenue", "average_ticket"],
    )
    assert not plan.write
    assert plan.frame is None
    assert plan.results[0].blocking
