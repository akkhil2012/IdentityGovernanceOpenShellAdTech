#!/usr/bin/env python3
"""Create schema and deterministic consent seed by invoking application startup."""
from governed_audience.main import seed_consents
seed_consents()
print("Seeded 1,000 deterministic consent records")
