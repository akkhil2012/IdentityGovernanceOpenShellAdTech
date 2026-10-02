from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

from .config import Settings


class Base(DeclarativeBase):
    pass


class Consent(Base):
    __tablename__ = "consents"
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(40), index=True)
    purpose: Mapped[str] = mapped_column(String(80))
    channel: Mapped[str] = mapped_column(String(40))
    destination: Mapped[str] = mapped_column(String(80))
    granted: Mapped[bool] = mapped_column(Boolean)
    version: Mapped[int] = mapped_column(Integer)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("customer_id", "purpose", "channel", "destination", "version"),)


class Workflow(Base):
    __tablename__ = "workflows"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    state: Mapped[str] = mapped_column(String(30))
    scenario: Mapped[str] = mapped_column(String(80))
    brief_json: Mapped[str] = mapped_column(Text)
    result_json: Mapped[str] = mapped_column(Text, default="{}")
    audience_json: Mapped[str] = mapped_column(Text, default="[]")
    audience_digest: Mapped[str] = mapped_column(String(64), default="")
    approval_digest: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class GrantState(Base):
    __tablename__ = "grant_state"
    grant_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    consumed_records: Mapped[int] = mapped_column(Integer, default=0)
    seen_nonces_json: Mapped[str] = mapped_column(Text, default="[]")


class ActivationIntent(Base):
    __tablename__ = "activation_intents"
    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String(40))
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True)
    binding_digest: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30))
    receipt_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String(40), index=True)
    event: Mapped[str] = mapped_column(String(80))
    detail_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def database(settings: Settings):
    kwargs = {"connect_args": {"check_same_thread": False}} if settings.database_url.startswith("sqlite") else {}
    # Keep an in-memory SQLite database on one connection so API test threads
    # observe the schema and state created during application initialization.
    if settings.database_url in {"sqlite://", "sqlite:///:memory:"}:
        kwargs["poolclass"] = StaticPool
    engine = create_engine(settings.database_url, **kwargs)
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)


def audit(db, workflow_id: str, event: str, detail: dict):
    safe = {k: v for k, v in detail.items() if k not in {"email", "name", "token", "signature"}}
    db.add(AuditEvent(workflow_id=workflow_id, event=event, detail_json=json.dumps(safe), created_at=datetime.now(timezone.utc)))
    db.commit()
