# Autonomous agent identity at runtime

## The distinction traditional user IAM misses

An autonomous agent is not the employee who started it. This demo records two
separate facts:

* **On behalf of:** `Fabio` supplied the business intent and remains part of the
  accountability chain.
* **Run as:** `agent:activation` is the workload principal created for one task.

Copying Fabio's long-lived roles onto the agent collapses those facts. It gives
changing autonomous behavior all of Fabio's ambient access, makes the audit log
misleading, and leaves authority alive after the task has ended.

## Scenario 1 — the unsafe inherited identity

Choose **Unsafe: agent inherits Fabio's user identity**. The activation agent
tries `export_raw_profiles`, which is outside its intended `activate` capability.
The demo marks the operation `EXECUTED_OUT_OF_SCOPE`: a traditional IAM check
sees `user:fabio`, not the agent's purpose or current task, and lets it through.
No real profile export occurs; this is a safe visualization of the anti-pattern.

## Scenario 2 — runtime identity fixes it

Choose **Fixed: determine the agent identity at runtime**. The trusted governance
service derives a short-lived identity from the workload, task, purpose,
capability, resource, destination, record budget, policy version, and delegation
chain. `Fabio` remains the `on_behalf_of` claim. The raw-profile export is denied,
then the separately authorized `activate` operation continues.

This is runtime determination rather than a static service account: every agent
gets a distinct signed child grant, cannot mint authority, cannot exceed its
parent, and is checked at the point of use for actor/task binding, expiry,
revocation, replay, and cumulative budget.

## NVIDIA OpenShell execution boundary

In `RUN_MODE=openshell`, the API sends the signed typed envelope to the configured
remote worker URL. Each worker image from `agents/Dockerfile.worker` is intended
to run as a separate NVIDIA OpenShell sandbox with its own workload identity and
least-authority policy. OpenShell contains execution; this repository's trusted
governance service decides authority. Startup fails closed unless every worker
URL, real sandbox ID, and broker secret is configured. Simulation demonstrates
the identity logic but is explicitly **not** isolation evidence.
