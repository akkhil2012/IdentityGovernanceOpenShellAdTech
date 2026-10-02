from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from governed_audience.db import Base
from governed_audience.governance import GovernanceDenied, GovernanceService

@pytest.fixture()
def state():
    engine=create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with sessionmaker(engine)() as db: yield GovernanceService("secret","v1"),db

def root(g):
    return g.mint(subject="root",task="t",purpose="ads",capabilities=["read","score"],resources=["allowed"],destinations=["mock"],record_budget=10,actor="root")

def test_delegation_must_narrow(state):
    g,db=state
    with pytest.raises(GovernanceDenied,match="exceeds parent"):
        g.mint(subject="child",task="t",purpose="ads",capabilities=["admin"],resources=["allowed"],destinations=["mock"],record_budget=1,actor="child",parent=root(g))

def test_replay_and_cumulative_budget(state):
    g,db=state; token=root(g)
    g.validate(db,token,actor="root",task="t",capability="read",resource="allowed",destination="mock",records=6,nonce="n1")
    with pytest.raises(GovernanceDenied,match="replay"): g.validate(db,token,actor="root",task="t",capability="read",resource="allowed",destination="mock",records=1,nonce="n1")
    with pytest.raises(GovernanceDenied,match="budget"): g.validate(db,token,actor="root",task="t",capability="read",resource="allowed",destination="mock",records=5,nonce="n2")

def test_revocation_and_actor_binding(state):
    g,db=state; token=root(g); g.revoke(db,token.claims.grant_id)
    with pytest.raises(GovernanceDenied,match="revoked"): g.validate(db,token,actor="root",task="t",capability="read",resource="allowed",destination="mock",records=1)
    fresh=root(g)
    with pytest.raises(GovernanceDenied,match="actor"): g.validate(db,fresh,actor="imposter",task="t",capability="read",resource="allowed",destination="mock",records=1)
