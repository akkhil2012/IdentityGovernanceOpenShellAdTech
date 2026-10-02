from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def now() -> datetime:
    return datetime.now(timezone.utc)


class CampaignBrief(BaseModel):
    name: str = "Loyalty upgrade"
    request: str = "Find customers likely to upgrade"
    purpose: str = "personalized_advertising"
    channel: str = "display"
    destination: str = "mock-dsp"
    max_audience: int = Field(100, ge=1, le=1000)


class Grant(BaseModel):
    grant_id: str
    issuer: str = "governance-service"
    audience: str = "task-broker"
    subject: str
    root_subject: str
    parent_grant: str | None = None
    task: str
    purpose: str
    capabilities: list[str]
    resources: list[str]
    destinations: list[str]
    record_budget: int
    expires_at: datetime
    policy_version: str
    actor: str
    # The human supplies intent, but is deliberately not the workload identity.
    on_behalf_of: str = "Fabio"
    identity_basis: str = "runtime-task-context"
    nonce: str


class SignedGrant(BaseModel):
    claims: Grant
    signature: str


class WorkerRequest(BaseModel):
    task_id: str
    agent: str
    operation: str
    payload: dict[str, Any]
    grant: SignedGrant


class WorkerResult(BaseModel):
    task_id: str
    agent: str
    sandbox_id: str
    status: Literal["ok", "denied", "error"]
    result: dict[str, Any] = {}


class WorkflowRequest(BaseModel):
    brief: CampaignBrief = CampaignBrief()
    scenario: str = "authorized_success"


class ConsentChange(BaseModel):
    customer_id: str
    purpose: str
    channel: str
    destination: str
    granted: bool


class RevokeRequest(BaseModel):
    grant_id: str


class ActivationRequest(BaseModel):
    workflow_id: str
    idempotency_key: str
    simulate_timeout: bool = False
