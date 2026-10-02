# Governed Audience

`governed-audience` is a reference AdTech/CDP control room. It turns a campaign brief into an eligibility-filtered, propensity-ranked audience, then issues a **GO**, **REVIEW**, or **NO-GO** decision. The demo keeps intent, profile data, model scores, consent, governance authority, and activation execution separate.

The headline demonstration compares **Unsafe: agent inherits Fabio's user identity** with **Fixed: determine the agent identity at runtime**. Fabio is recorded as the human on whose behalf the task was requested, never as the autonomous workload principal. The unsafe scenario shows a raw-profile export apparently succeeding outside the activation agent's scope; the fixed scenario blocks that same operation and permits only the task-bound activation. See [`docs/runtime-identity.md`](docs/runtime-identity.md).

> **Safety boundary:** the default `simulation` mode is conspicuously labeled and does not provide process isolation. `openshell` mode never falls back: startup fails unless a broker secret and six sandbox IDs are supplied. The destination is always a local mock; nothing sends ads or email.

## Quick start (deterministic simulation)

Requirements: Docker 24+ with Compose v2, or Python 3.12+, Node 22+, and PostgreSQL 16.

```bash
cp .env.example .env
docker compose up --build
# UI: http://localhost:5173  API/docs: http://localhost:8000/docs
```

Without containers:

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements.lock
export DATABASE_URL=sqlite:///./governed_audience.db RUN_MODE=simulation
python scripts/seed.py
uvicorn governed_audience.main:app --app-dir apps/api --reload
# second terminal
cd apps/web && npm ci && npm run dev
```

Tests: `pytest`; frontend: `cd apps/web && npm ci && npm run build`.

## Modes

* `RUN_MODE=simulation`: in-process deterministic workers, fixed seed, no model credentials. Responses and the UI say **SIMULATION — NOT ISOLATED**.
* `RUN_MODE=openshell`: coordinator dispatches authenticated, signed task envelopes to separately deployed worker URLs. Set `INTENT_WORKER_URL` through `ACTIVATION_WORKER_URL`, corresponding `*_SANDBOX_ID` values, and `BROKER_SHARED_SECRET`. Startup refuses missing values. See [`docs/openshell.md`](docs/openshell.md); infrastructure verification remains an operator gate.

The coordinator has an optional Google ADK dependency for real deployments. Its boundary is deliberately behind typed `WorkerRequest`/`WorkerResult` adapters: authority is minted only by the trusted API, never by an agent. This repository pins `google-adk==1.17.0`; see the documentation caveat and verification procedure in [`docs/openshell.md`](docs/openshell.md).

## Repository map

* `apps/api/governed_audience`: FastAPI API, coordinator, deterministic scoring, governance and mock activation.
* `apps/web`: React/Vite campaign control room.
* `migrations`: PostgreSQL schema; the API also creates equivalent tables for a local demo.
* `agents`: one NVIDIA OpenShell workload image entry point and least-authority policy template per specialist.
* `scripts`: reproducible seed and explicitly gated OpenShell launch/validation scripts.
* `docs`: architecture/threat model, model card, isolation evidence guide, and ten-minute demo.

## Core invariants

Eligibility is evaluated before scoring. Consent is a deterministic `(customer, purpose, channel, destination, version)` fact and is checked for audience approval and again immediately before execution. Confidence is never consent. Grants are signed, short-lived, actor-bound and narrowed through delegation; the API checks issuer, audience, expiry, revocation, task/root/parent binding, capability/resource/destination scope, cumulative record budget and one-use nonce. Approval and execution permits bind the immutable audience digest, campaign, purpose, channel and destination. Activation intents and receipts are durable and idempotent; an unknown outcome is surfaced for reconciliation, never blindly retried.

## Documentation

* [Architecture and threat model](docs/architecture.md)
* [Model card and evaluation](docs/model-card.md)
* [OpenShell/ADK setup and evidence](docs/openshell.md)
* [Ten-minute demonstration](docs/demo.md)

## Current limitations

Synthetic scores are illustrative, not validated predictions and do not demonstrate incremental lift. HMAC is used for a self-contained demo (production should use asymmetric KMS signing). Simulation uses SQLite when selected; PostgreSQL is the supported deployment state store. The checked-in OpenShell policy files are reviewable least-authority manifests, but they **must be validated against the installed pinned OpenShell release before real mode**; this environment could not reach official documentation or run OpenShell, so real sandbox tests are explicitly not claimed.
