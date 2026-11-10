"""Normalize frames before a gate sees them, so CSV reloads compare cleanly."""

from __future__ import annotations

import pandas as pd

from gates.checks import as_date


def normalize_monthly(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    normalized["purchase_month"] = normalized["purchase_month"].map(
        lambda value: as_date(value).isoformat()
    )
    normalized["delivered_orders"] = normalized["delivered_orders"].astype(int)
    normalized["product_revenue"] = normalized["product_revenue"].astype(float).round(2)
    normalized["average_ticket"] = normalized["average_ticket"].astype(float).round(2)
    columns = ["purchase_month", "delivered_orders", "product_revenue", "average_ticket"]
    return normalized.loc[:, columns].sort_values("purchase_month").reset_index(drop=True)


def normalize_repurchase(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    normalized["cohort_month"] = normalized["cohort_month"].map(
        lambda value: as_date(value).isoformat()
    )
    normalized["mature_customers"] = normalized["mature_customers"].astype(int)
    normalized["repurchasing_customers"] = normalized["repurchasing_customers"].astype(int)
    normalized["repurchase_rate_indicative"] = (
        normalized["repurchase_rate_indicative"].astype(float).round(6)
    )
    columns = [
        "cohort_month",
        "mature_customers",
        "repurchasing_customers",
        "repurchase_rate_indicative",
    ]
    return normalized.loc[:, columns].sort_values("cohort_month").reset_index(drop=True)
