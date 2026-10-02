"""Minimal remote worker entry point; deployment supplies broker authentication middleware."""
import os
from fastapi import FastAPI, Header, HTTPException
from governed_audience.models import WorkerRequest, WorkerResult

AGENT=os.environ["AGENT_NAME"]
SANDBOX_ID=os.environ["SANDBOX_ID"]
SECRET=os.environ["BROKER_SHARED_SECRET"]
app=FastAPI(docs_url=None,redoc_url=None)

@app.post("/tasks")
def task(request: WorkerRequest, x_broker_signature: str=Header()):
    import hashlib
    expected=hashlib.sha256((SECRET+request.task_id).encode()).hexdigest()
    if request.agent != AGENT or x_broker_signature != expected: raise HTTPException(403,"broker or actor binding denied")
    return WorkerResult(task_id=request.task_id,agent=AGENT,sandbox_id=SANDBOX_ID,status="ok",result={"accepted":True})
