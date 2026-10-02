# Architecture and threat model

```text
browser ──SSE/HTTPS──> trusted FastAPI governance plane ──signed task──> authenticated broker
                           │                                   ├─ intent sandbox
 Postgres: consent, grants,│ workflows, intents, receipts     ├─ profile sandbox
                           │                                   ├─ propensity sandbox
                           └──── mock destination              ├─ audience sandbox
                                                               ├─ consent sandbox
                                                               └─ activation sandbox
```

The trusted plane owns policy, signing, current consent, approval and execution. The ADK coordinator owns sequencing only. Each typed worker adapter exchanges a task ID, operation, minimal payload, signed grant, sandbox ID, status and minimal result. In real mode each URL must identify a worker in its own named OpenShell sandbox; startup checks all six IDs/URLs and refuses fallback.

## Trust boundaries and threats

Agents, campaign text, browser input and the mock destination are untrusted. PostgreSQL, the governance signing key and policy configuration are trusted operational dependencies. Threats include prompt-driven data access, confused deputy/delegation escalation, forged/replayed/revoked grants, data over-collection, consent inferred from behavior, audience substitution, stale approval, duplicated activation, SSRF/exfiltration and misleading isolation claims.

Controls are: distinct workload actors; five-minute HMAC grants with issuer/audience/actor/task/root/parent/purpose/capability/resource/destination/budget/policy bindings; strict delegation set containment; durable cumulative usage and nonce replay state; endpoint checks; allow-listed profile projection; consent version history and execution-time lookup; canonical SHA-256 audience and permit bindings; durable idempotency records; unknown outcome reconciliation; sanitized audit data; and sandbox filesystem/process/network/provider restrictions. Human review may resolve ambiguity but cannot override a consent or policy denial.

Residual risks: the demo HMAC key is symmetric, worker HTTP authentication is a shared-secret construction rather than production mTLS, database encryption/HA are deployment concerns, synthetic model quality is not evidence of business performance, and policy enforcement depends on separately verified OpenShell infrastructure.
