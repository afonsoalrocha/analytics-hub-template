"""Deterministic synthetic extract shaped like the public Olist tables.

The series is the offline fallback. It is seeded, small, and original.
November 2017 has twice the daily order count of the surrounding months, so
the variation gate warns once. September 2018 stops on the 10th, so that
month stays out of the mart. Payments equal price plus freight.
"""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta

import pandas as pd

STATES = ["SP", "RJ", "MG", "RS", "PR", "BA", "SC", "PE"]
REPEATERS = [f"person_r_{index:02d}" for index in range(10)]
EARLY_ONCE = [f"person_e_{index:02d}" for index in range(10)]
LATE_ONCE = [f"person_l_{index:02d}" for index in range(10)]


def daily_quota(day: date) -> int:
    if day.year == 2016:
        return 2
    if day.year == 2017 and day.month == 11:
        return 8
    return 4


def iter_days() -> list[date]:
    days = [date(2016, 12, 1), date(2016, 12, 15)]
    current = date(2017, 1, 1)
    while current <= date(2018, 8, 31):
        days.append(current)
        current += timedelta(days=1)
    current = date(2018, 9, 1)
    while current <= date(2018, 9, 10):
        days.append(current)
        current += timedelta(days=1)
    return days


def build_frames(seed: int = 42) -> dict[str, pd.DataFrame]:
    rng = random.Random(seed)
    early_remaining = list(EARLY_ONCE)
    late_remaining = list(LATE_ONCE)
    repeater_index = 0
    orders: list[dict[str, object]] = []
    items: list[dict[str, object]] = []
    customers: list[dict[str, object]] = []
    payments: list[dict[str, object]] = []
    order_number = 0

    def add_order(day: date, person: str, status: str, *, with_items: bool) -> None:
        nonlocal order_number
        order_number += 1
        purchased = datetime(day.year, day.month, day.day, 12, 0, 0)
        order_id = f"ord_{order_number:06d}"
        customer_id = f"cust_{order_number:06d}"
        delivered = status == "delivered"
        orders.append(
            {
                "order_id": order_id,
                "customer_id": customer_id,
                "order_status": status,
                "order_purchase_timestamp": purchased,
                "order_approved_at": purchased + timedelta(hours=1) if delivered else pd.NaT,
                "order_delivered_carrier_date": purchased + timedelta(days=2)
                if delivered
                else pd.NaT,
                "order_delivered_customer_date": purchased + timedelta(days=7)
                if delivered
                else pd.NaT,
                "order_estimated_delivery_date": purchased + timedelta(days=10),
            }
        )
        customers.append(
            {
                "customer_id": customer_id,
                "customer_unique_id": person,
                "customer_zip_code_prefix": None,
                "customer_city": None,
                "customer_state": STATES[order_number % len(STATES)],
            }
        )
        if not with_items:
            return
        price_cents = rng.randint(4000, 18000)
        freight_cents = rng.randint(800, 2500)
        items.append(
            {
                "order_id": order_id,
                "order_item_id": 1,
                "product_id": f"sku_{order_number % 25:04d}",
                "seller_id": f"seller_{order_number % 5:02d}",
                "shipping_limit_date": purchased + timedelta(days=3),
                "price": price_cents / 100,
                "freight_value": freight_cents / 100,
            }
        )
        payments.append(
            {
                "order_id": order_id,
                "payment_sequential": 1,
                "payment_type": "credit_card",
                "payment_installments": 1,
                "payment_value": (price_cents + freight_cents) / 100,
            }
        )

    for day in iter_days():
        for slot in range(daily_quota(day)):
            if day.year == 2017 and day.month == 1 and slot == 0 and early_remaining:
                person = early_remaining.pop(0)
            elif day.year == 2018 and day.month == 7 and slot == 0 and late_remaining:
                person = late_remaining.pop(0)
            else:
                person = REPEATERS[repeater_index % len(REPEATERS)]
                repeater_index += 1
            add_order(day, person, "delivered", with_items=True)

    add_order(date(2017, 1, 15), "person_canceled", "canceled", with_items=False)

    return {
        "orders": pd.DataFrame(orders),
        "order_items": pd.DataFrame(items),
        "customers": pd.DataFrame(customers),
        "payments": pd.DataFrame(payments),
    }
