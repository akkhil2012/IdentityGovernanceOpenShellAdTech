import os
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["RUN_MODE"] = "simulation"

import pytest
from fastapi.testclient import TestClient
from governed_audience.main import app, seed_consents

@pytest.fixture()
def client():
    seed_consents()
    with TestClient(app) as c: yield c
