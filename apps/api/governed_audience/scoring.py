from __future__ import annotations

import random
from math import exp

SEED = 20260417


def generate_profiles(count: int = 1000) -> list[dict]:
    rng = random.Random(SEED)
    regions = ("north", "south", "east", "west")
    profiles = []
    for i in range(count):
        visits = rng.randint(0, 30)
        purchases = rng.randint(0, min(visits, 8))
        days = rng.randint(0, 365)
        value = round(rng.uniform(15, 600), 2) if purchases else 0.0
        profiles.append({"customer_id": f"C{i+1:04d}", "visits_30d": visits, "purchases_180d": purchases,
                         "days_since_purchase": days, "avg_order_value": value, "region": regions[i % 4],
                         "eligible": i % 29 != 0})
    return profiles


def score(profile: dict) -> float:
    """Fixed, transparent illustrative logistic baseline; no sensitive attributes."""
    z = -2.2 + .055 * profile["visits_30d"] + .24 * profile["purchases_180d"] - .003 * profile["days_since_purchase"] + .0012 * profile["avg_order_value"]
    return round(1 / (1 + exp(-z)), 6)
