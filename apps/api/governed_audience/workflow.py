from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import desc, select

from .config import AGENTS, Settings
from .db import Consent, Workflow, audit
from .governance import GovernanceDenied, GovernanceService
from .models import CampaignBrief, SignedGrant, WorkerRequest, WorkerResult
from .scoring import generate_profiles, score


SCENARIOS = {
    "fabio_static_identity": "Unsafe: agent inherits Fabio's user identity",
    "runtime_agent_identity": "Fixed: determine the agent identity at runtime",
    "authorized_success": "Authorized successful activation",
    "missing_consent": "High propensity with missing consent",
    "consent_withdrawal": "Consent withdrawal after approval",
    "forbidden_field": "Forbidden profile-field access",
    "forbidden_network": "Forbidden network access",
    "capability_escalation": "Agent capability escalation",
    "grant_revocation": "Grant revocation during execution",
    "audience_mutation": "Audience mutation after approval",
    "activation_timeout": "Activation timeout and duplicate retry",
}


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class WorkerAdapter:
    def __init__(self, settings: Settings): self.settings = settings

    async def invoke(self, request: WorkerRequest) -> WorkerResult:
        sandbox = getattr(self.settings, f"{request.agent}_sandbox_id")
        if self.settings.run_mode == "simulation":
            await asyncio.sleep(0)
            return WorkerResult(task_id=request.task_id, agent=request.agent, sandbox_id=sandbox, status="ok", result={"accepted": True})
        url = getattr(self.settings, f"{request.agent}_worker_url")
        signature = hashlib.sha256((self.settings.broker_shared_secret + request.task_id).encode()).hexdigest()
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(f"{url.rstrip('/')}/tasks", json=request.model_dump(mode="json"), headers={"X-Broker-Signature": signature})
            response.raise_for_status()
            return WorkerResult.model_validate(response.json())


class Coordinator:
    """ADK coordination boundary with typed remote adapters; deterministic in simulation."""
    def __init__(self, settings: Settings, session_factory):
        self.settings, self.Session = settings, session_factory
        self.gov, self.adapter = GovernanceService(settings.governance_signing_key, settings.policy_version), WorkerAdapter(settings)

    def _current_consent(self, db, customer_id: str, brief: CampaignBrief) -> bool:
        stmt = select(Consent).where(Consent.customer_id == customer_id, Consent.purpose == brief.purpose,
            Consent.channel == brief.channel, Consent.destination == brief.destination).order_by(desc(Consent.version)).limit(1)
        row = db.scalar(stmt)
        return bool(row and row.granted)

    async def run(self, brief: CampaignBrief, scenario: str) -> dict:
        if scenario not in SCENARIOS: raise ValueError("unknown scenario")
        wid, task = str(uuid.uuid4()), f"campaign:{uuid.uuid4()}"
        with self.Session() as db:
            wf = Workflow(id=wid, state="running", scenario=scenario, brief_json=brief.model_dump_json(), created_at=datetime.now(timezone.utc))
            db.add(wf); db.commit()
            timeline, grants = [], []
            identity_evidence = {
                "on_behalf_of": "Fabio",
                "human_identity_is_authority": scenario == "fabio_static_identity",
                "explanation": "Fabio supplied the intent; the autonomous agent remains a distinct runtime principal.",
            }
            root = self.gov.mint(subject="coordinator", task=task, purpose=brief.purpose,
                capabilities=["interpret", "read_profile", "score", "build_audience", "check_consent", "activate"],
                resources=["campaign", "profile.allowed", "scores", "consent", "audience"], destinations=[brief.destination], record_budget=6000, actor="coordinator")
            for index, agent in enumerate(AGENTS):
                cap = {"intent":"interpret","profile":"read_profile","propensity":"score","audience":"build_audience","consent":"check_consent","activation":"activate"}[agent]
                resource = {"intent":"campaign","profile":"profile.allowed","propensity":"scores","audience":"audience","consent":"consent","activation":"audience"}[agent]
                try:
                    requested_cap = "admin" if scenario == "capability_escalation" and agent == "audience" else cap
                    child = self.gov.mint(subject=f"agent:{agent}", task=task, purpose=brief.purpose, capabilities=[requested_cap], resources=[resource], destinations=[brief.destination], record_budget=1000, actor=f"agent:{agent}", parent=root)
                    grants.append(child)
                    if scenario == "fabio_static_identity" and agent == "activation":
                        # Deliberately model the anti-pattern without performing a real export:
                        # a shared user credential makes an out-of-scope operation appear valid.
                        timeline.append({"agent":agent,"status":"ok","sandbox_id":getattr(self.settings, f"{agent}_sandbox_id"),"governance":"BYPASSED — Fabio IAM","reason":"export_raw_profiles executed outside the activation agent scope"})
                        identity_evidence |= {"principal":"user:fabio","attempted":"export_raw_profiles","outcome":"EXECUTED_OUT_OF_SCOPE","risk":"The audit trail attributes autonomous behavior to a human user."}
                        continue
                    if scenario == "runtime_agent_identity" and agent == "activation":
                        try:
                            self.gov.validate(db, child, actor=f"agent:{agent}", task=task, capability="export_raw_profiles", resource="profile.raw", destination=brief.destination, records=1, nonce=f"{child.claims.nonce}:probe")
                        except GovernanceDenied as exc:
                            identity_evidence |= {"principal":"agent:activation","runtime_grant":child.claims.grant_id,"attempted":"export_raw_profiles","outcome":"BLOCKED_OUT_OF_SCOPE","reason":str(exc),"allowed_operation":"activate"}
                    if scenario == "grant_revocation" and agent == "activation": self.gov.revoke(db, child.claims.grant_id)
                    if scenario == "forbidden_field" and agent == "profile": resource = "profile.ssn"
                    if scenario == "forbidden_network" and agent == "activation":
                        raise GovernanceDenied("sandbox policy denied outbound destination evil.example")
                    self.gov.validate(db, child, actor=f"agent:{agent}", task=task, capability=cap, resource=resource, destination=brief.destination, records=1, nonce=f"{child.claims.nonce}:{index}")
                    result = await self.adapter.invoke(WorkerRequest(task_id=task, agent=agent, operation=cap, payload={"workflow_id":wid}, grant=child))
                    timeline.append({"agent":agent,"status":result.status,"sandbox_id":result.sandbox_id,"governance":"allowed"})
                except GovernanceDenied as exc:
                    timeline.append({"agent":agent,"status":"denied","sandbox_id":getattr(self.settings, f"{agent}_sandbox_id"),"governance":"denied","reason":str(exc)})
                    wf.state = "no-go"; wf.result_json = json.dumps({"decision":"NO-GO","reason":str(exc),"timeline":timeline,"grants":[g.claims.model_dump(mode="json") for g in grants]}); db.commit()
                    audit(db, wid, "governance.denied", {"agent":agent,"reason":str(exc)})
                    return json.loads(wf.result_json) | {"workflow_id":wid, "mode":self.settings.run_mode}

            profiles = [p for p in generate_profiles() if p["eligible"]]  # eligibility precedes scoring
            ranked = sorted(({**p, "score":score(p)} for p in profiles), key=lambda p:p["score"], reverse=True)
            if scenario == "missing_consent": ranked[0]["customer_id"] = "C0029"
            approved, excluded = [], {}
            for p in ranked:
                if len(approved) >= brief.max_audience: break
                if self._current_consent(db, p["customer_id"], brief): approved.append({"customer_id":p["customer_id"],"score":p["score"]})
                else: excluded["missing_consent"] = excluded.get("missing_consent", 0) + 1
            audience_digest = digest(approved)
            if scenario == "consent_withdrawal" and approved:
                member = approved[0]["customer_id"]
                current = db.scalar(select(Consent).where(Consent.customer_id == member,
                    Consent.purpose == brief.purpose, Consent.channel == brief.channel,
                    Consent.destination == brief.destination).order_by(desc(Consent.version)).limit(1))
                db.add(Consent(customer_id=member, purpose=brief.purpose, channel=brief.channel,
                    destination=brief.destination, granted=False, version=current.version + 1,
                    recorded_at=datetime.now(timezone.utc)))
                db.commit()
            if scenario == "audience_mutation": approval_digest = digest(approved + [{"customer_id":"MUTATED","score":1}])
            else: approval_digest = audience_digest
            hard_no = scenario == "missing_consent" and not self._current_consent(db, "C0029", brief)
            decision = "NO-GO" if hard_no else ("REVIEW" if scenario == "fabio_static_identity" or not approved else "GO")
            result = {"decision":decision,"reason":"required consent missing" if hard_no else ("unsafe shared user identity allowed an out-of-scope action" if scenario == "fabio_static_identity" else "runtime agent identity and policy checks passed"),
                "timeline":timeline,"funnel":{"generated":1000,"eligible":len(profiles),"approved":len(approved),"excluded":excluded},
                "audience_digest":audience_digest,"grants":[g.claims.model_dump(mode="json") for g in grants], "identity_evidence":identity_evidence}
            wf.state=decision.lower(); wf.audience_json=json.dumps(approved); wf.audience_digest=audience_digest; wf.approval_digest=approval_digest; wf.result_json=json.dumps(result); db.commit()
            audit(db, wid, "workflow.decided", {"decision":decision,"audience_count":len(approved)})
            return result | {"workflow_id":wid,"mode":self.settings.run_mode}
