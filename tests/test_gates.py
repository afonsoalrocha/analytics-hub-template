from datetime import date

import pandas as pd

from gates.checks import (
    check_anomalous_variation,
    check_frozen_history,
    check_grain_uniqueness,
    check_metric_status,
    check_partial_month,
    check_publication_metadata,
    check_reconciliation,
    check_scope_completeness,
    check_temporal_coverage,
    check_value_domain,
    complete_months,
)
from gates.results import Severity
from gates.runner import exit_code


def test_complete_months_drop_gaps_and_the_open_month():
    days = [date(2017, 1, day) for day in range(1, 32)]
    days.append(date(2017, 2, 1))
    ready = complete_months(days)
    assert ready == [date(2017, 1, 1)]


def test_grain_uniqueness_blocks_on_a_duplicate():
    frame = pd.DataFrame({"purchase_month": ["2017-01-01", "2017-01-01"], "orders": [1, 2]})
    result = check_grain_uniqueness(frame, ["purchase_month"])
    assert result.blocking
    assert result.severity is Severity.BLOCK


def test_temporal_coverage_and_partial_month_share_the_calendar():
    days = [date(2017, 1, day) for day in range(1, 31)]
    published = [date(2017, 1, 1)]
    assert check_temporal_coverage(days, published).blocking
    assert check_partial_month(published, days).blocking
    full = [date(2017, 1, day) for day in range(1, 32)]
    assert check_temporal_coverage(full, published).passed
    assert check_partial_month(published, full).passed


def test_scope_completeness_does_not_treat_absence_as_zero():
    result = check_scope_completeness(
        [date(2017, 1, 1), date(2017, 2, 1)],
        [date(2017, 1, 1)],
        label="Closed months",
    )
    assert result.blocking
    assert "left unpublished" in result.message


def test_value_domain_blocks_a_negative_and_a_zero_denominator():
    frame = pd.DataFrame({"delivered_orders": [0], "product_revenue": [-1.0]})
    result = check_value_domain(
        frame,
        ["delivered_orders", "product_revenue"],
        strictly_positive=["delivered_orders"],
    )
    assert result.blocking


def test_reconciliation_warns_above_tolerance_and_does_not_block():
    frame = pd.DataFrame(
        {
            "purchase_month": [date(2017, 3, 1)],
            "item_gmv": [100.0],
            "payment_gmv": [103.0],
        }
    )
    result = check_reconciliation(
        frame,
        left="item_gmv",
        right="payment_gmv",
        key="purchase_month",
        tolerance=0.005,
    )
    assert not result.passed
    assert result.severity is Severity.WARN
    assert not result.blocking
    assert exit_code([result]) == 0


def test_variation_warns_above_fifty_percent():
    frame = pd.DataFrame(
        {
            "purchase_month": [date(2017, 10, 1), date(2017, 11, 1)],
            "delivered_orders": [100, 160],
        }
    )
    result = check_anomalous_variation(
        frame,
        column="delivered_orders",
        key="purchase_month",
        threshold=0.5,
    )
    assert result.state == "warn"
    assert "2017-11-01" in result.message


def test_frozen_history_blocks_a_rewrite_and_allows_the_first_close():
    current = pd.DataFrame(
        {
            "purchase_month": ["2017-01-01"],
            "delivered_orders": [10],
            "product_revenue": [100.0],
        }
    )
    first = check_frozen_history(
        None,
        current,
        key="purchase_month",
        columns=["delivered_orders", "product_revenue"],
    )
    assert first.passed
    rewritten = current.copy()
    rewritten["delivered_orders"] = [11]
    second = check_frozen_history(
        current,
        rewritten,
        key="purchase_month",
        columns=["delivered_orders", "product_revenue"],
    )
    assert second.blocking


def test_metric_status_rejects_a_blocked_column_and_a_bare_indicative_name():
    catalog = [
        {"id": "delivered_orders", "status": "certified"},
        {"id": "repurchase_rate", "status": "indicative"},
        {"id": "visit_to_order_conversion", "status": "blocked"},
    ]
    blocked = check_metric_status(
        ["delivered_orders", "visit_to_order_conversion"],
        catalog,
        indicative_suffix="_indicative",
    )
    assert blocked.blocking
    bare = check_metric_status(
        ["repurchase_rate"],
        catalog,
        indicative_suffix="_indicative",
    )
    assert bare.blocking
    clean = check_metric_status(
        ["delivered_orders", "repurchase_rate_indicative"],
        catalog,
        indicative_suffix="_indicative",
    )
    assert clean.passed


def test_publication_metadata_requires_period_filters_units_and_load_time():
    missing = check_publication_metadata({}, ["delivered_orders"])
    assert missing.blocking
    present = check_publication_metadata(
        {
            "period_start": "2017-01-01",
            "period_end": "2017-01-31",
            "filters": ["order_status = 'delivered'"],
            "units": {"delivered_orders": "orders"},
            "loaded_at": "2026-11-10T00:00:00+00:00",
        },
        ["delivered_orders"],
    )
    assert present.passed
