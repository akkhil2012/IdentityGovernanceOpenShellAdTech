from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, select

from .config import AGENTS, Settings
from .db import ActivationIntent, AuditEvent, Consent, Workflow, audit, database
from .governance import GovernanceService
from .models import ActivationRequest, ConsentChange, RevokeRequest, WorkflowRequest
from .scoring import generate_profiles
from .workflow import Coordinator, SCENARIOS, digest

settings = Settings()
settings.validate_runtime()
Session = database(settings)
coordinator = Coordinator(settings, Session)
app = FastAPI(title="Governed Audience API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])


def db_session():
    with Session() as db: yield db


@app.on_event("startup")
def seed_consents():
    with Session() as db:
        if db.scalar(select(Consent.id).limit(1)) is None:
            now = datetime.now(timezone.utc)
            for p in generate_profiles():
                db.add(Consent(customer_id=p["customer_id"], purpose="personalized_advertising", channel="display", destination="mock-dsp", granted=p["customer_id"] != "C0029", version=1, recorded_at=now))
            db.commit()


@app.get("/health")
def health():
    return {"status":"ok","mode":settings.run_mode,"isolated":settings.run_mode == "openshell"}


@app.get("/api/config")
def config():
    return {"mode":settings.run_mode,"isolated":settings.run_mode == "openshell","scenarios":SCENARIOS,
            "sandboxes":{a:getattr(settings, f"{a}_sandbox_id") for a in AGENTS}}


@app.get("/api/profiles")
def profiles(offset: int = 0, limit: int = 25):
    rows = generate_profiles()[offset:offset + min(limit, 100)]
    return {"total":1000,"items":rows}


@app.post("/api/workflows")
async def create_workflow(request: WorkflowRequest):
    try: return await coordinator.run(request.brief, request.scenario)
    except ValueError as exc: raise HTTPException(400, str(exc)) from exc


@app.get("/api/workflows/{workflow_id}")
def get_workflow(workflow_id: str, db=Depends(db_session)):
    wf = db.get(Workflow, workflow_id)
    if not wf: raise HTTPException(404, "workflow not found")
    return json.loads(wf.result_json) | {"workflow_id":wf.id,"mode":settings.run_mode}


@app.get("/api/workflows/{workflow_id}/events")
async def events(workflow_id: str, db=Depends(db_session)):
    rows = db.scalars(select(AuditEvent).where(AuditEvent.workflow_id == workflow_id).order_by(AuditEvent.id)).all()
    async def stream():
        for row in rows:
            yield f"event: audit\ndata: {json.dumps({'event':row.event,'detail':json.loads(row.detail_json),'at':row.created_at.isoformat()})}\n\n"
            await asyncio.sleep(.05)
        yield "event: complete\ndata: {}\n\n"
    return StreamingResponse(stream(), media_type="text/event-stream")


@app.post("/api/consents")
def change_consent(change: ConsentChange, db=Depends(db_session)):
    stmt = select(Consent).where(Consent.customer_id==change.customer_id, Consent.purpose==change.purpose,
        Consent.channel==change.channel, Consent.destination==change.destination).order_by(desc(Consent.version)).limit(1)
    current = db.scalar(stmt); version = (current.version if current else 0) + 1
    db.add(Consent(**change.model_dump(), version=version, recorded_at=datetime.now(timezone.utc))); db.commit()
    return {"status":"recorded","version":version}


@app.post("/api/grants/revoke")
def revoke(req: RevokeRequest, db=Depends(db_session)):
    GovernanceService.revoke(db, req.grant_id)
    return {"status":"revoked","grant_id":req.grant_id}


@app.post("/api/activate")
def activate(req: ActivationRequest, db=Depends(db_session)):
    existing = db.scalar(select(ActivationIntent).where(ActivationIntent.idempotency_key==req.idempotency_key))
    if existing: return json.loads(existing.receipt_json) | {"idempotent_replay":True,"status":existing.status}
    wf = db.get(Workflow, req.workflow_id)
    if not wf: raise HTTPException(404, "workflow not found")
    brief = json.loads(wf.brief_json); audience = json.loads(wf.audience_json)
    binding = digest({"audience_digest":wf.audience_digest,"campaign":brief["name"],"purpose":brief["purpose"],"channel":brief["channel"],"destination":brief["destination"]})
    intent = ActivationIntent(workflow_id=wf.id,idempotency_key=req.idempotency_key,binding_digest=binding,status="pending",created_at=datetime.now(timezone.utc))
    db.add(intent); db.commit()  # durable before side effect
    if wf.audience_digest != wf.approval_digest:
        intent.status="denied"; intent.receipt_json=json.dumps({"decision":"NO-GO","reason":"audience changed after approval"}); db.commit(); return json.loads(intent.receipt_json)
    for member in audience:
        stmt=select(Consent).where(Consent.customer_id==member["customer_id"], Consent.purpose==brief["purpose"], Consent.channel==brief["channel"], Consent.destination==brief["destination"]).order_by(desc(Consent.version)).limit(1)
        if not (current := db.scalar(stmt)) or not current.granted:
            intent.status="denied"; intent.receipt_json=json.dumps({"decision":"NO-GO","reason":"consent not current at execution","customer_id":member["customer_id"]}); db.commit(); return json.loads(intent.receipt_json)
    if req.simulate_timeout or wf.scenario == "activation_timeout":
        intent.status="unknown"; intent.receipt_json=json.dumps({"decision":"REVIEW","reason":"unknown destination outcome; reconcile before retry","binding_digest":binding}); db.commit(); return json.loads(intent.receipt_json)
    receipt={"decision":"GO","receipt_id":"mock-"+hashlib.sha256(req.idempotency_key.encode()).hexdigest()[:12],"records":len(audience),"binding_digest":binding,"destination":"mock-dsp","sent":False}
    intent.status="succeeded"; intent.receipt_json=json.dumps(receipt); db.commit(); audit(db,wf.id,"activation.receipted",{"receipt_id":receipt["receipt_id"],"records":len(audience)})
    return receipt
