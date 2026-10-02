# Google ADK and NVIDIA OpenShell deployment gate

## Documentation status and pins

Before implementation we attempted to read the official Google ADK installation documentation, NVIDIA OpenShell documentation and NVIDIA/OpenShell releases. The build environment's outbound proxy returned HTTP 403, and the web research service returned HTTP 401. Therefore this repository does **not** assert unverified OpenShell CLI syntax or policy-schema fields. That is a deliberate safety property: invented isolation evidence would be worse than a clearly blocked infrastructure gate.

The application dependency is pinned to `google-adk==1.17.0` and the supported application host is Linux x86-64, Python 3.12, Node 22, Docker 24+/Compose v2, and PostgreSQL 16. `scripts/verify_external_tools.sh` records installed versions and fails until an operator supplies `OPEN_SHELL_VERSION`, an installed `openshell` executable, and an approved policy validation command copied from the official documentation for that exact release. OpenShell itself is consequently **operator-pinned**, not falsely pinned here. Re-run official compatibility review before production or lock regeneration.

## Real-mode procedure

1. On a supported Linux host, consult the current official OpenShell release documentation. Pin its package/image digest and record it in deployment inventory.
2. Translate each schema-neutral contract in `agents/policies/*.contract.json` into that release's documented policy schema. Do not rename an unrecognized field into something plausible.
3. Build six distinct images from `agents/<agent>/Dockerfile`. Give each a different workload identity and no host, Docker, Kubernetes, cloud-admin or governance signing credentials.
4. Use only the documented release CLI/API to create six named sandboxes and apply/validate their policies. Run `scripts/verify_external_tools.sh`, setting `OPEN_SHELL_VALIDATE_COMMAND` to that documented non-mutating validation command.
5. Record actual sandbox IDs, image digests, policy digests, OpenShell version, validation output and timestamps in `evidence/openshell-evidence.json` (start from the template). Placeholder/simulation IDs are not evidence.
6. Put a mutually authenticated broker in front of the workers. Set all six `*_WORKER_URL`, all six actual `*_SANDBOX_ID`, `BROKER_SHARED_SECRET`, and `RUN_MODE=openshell`. The API refuses to start if one is absent and never silently falls back.
7. Execute the forbidden filesystem/process/network/provider tests inside each real sandbox. Preserve tool output as evidence. Until this happens, report these tests **not run**, not passed.

Google ADK is the real-mode coordination library, not an authorization system. The coordinator must call the typed adapters in `workflow.py`; workers do not receive the governance signing key or database administration credentials. Model provider credentials, if used, are injected only into workers whose verified contract permits that provider destination.

## Policy intent (schema neutral)

All workers may execute only the worker entry point, read their immutable application tree and CA bundle, and write only `/tmp`. Intent receives campaign text, Profile receives the approved non-sensitive projection, Propensity receives numeric features, Audience receives IDs/scores, Consent receives IDs and consent tuple, and Activation receives an immutable permit/payload. Network is broker-only except an explicitly required model provider and the Activation worker's mock destination. Every other destination, host mount, shell/toolchain, privilege escalation and provider credential is denied.

This repository intentionally does not call a JSON contract an “applied OpenShell policy.” Actual policy evidence is an external deployment deliverable blocked here by unavailable official documentation and runtime.
