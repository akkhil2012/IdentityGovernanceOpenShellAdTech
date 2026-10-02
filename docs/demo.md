# Ten-minute demonstration

**0:00–1:00** Start simulation with Docker Compose. Point out the amber “SIMULATION — NOT ISOLATED” banner and `/health` response. Explain that real mode fails closed.

**1:00–2:00** Review the fixed campaign purpose/channel/destination and profile explorer. Explain that behavior, score and confidence cannot grant consent.

**2:00–3:30** Run **Authorized successful activation**. Follow six distinct worker cards, sandbox labels, funnel, exclusions and narrowed delegation grants. Activate the mock destination and inspect its payload-binding digest and `sent: false` receipt.

**3:30–4:30** Submit the same activation idempotency key. Show the same receipt and `idempotent_replay`; no second side effect occurs.

**4:30–5:30** Run **High propensity with missing consent**. Show NO-GO. Emphasize that review cannot override it.

**5:30–6:30** Run success, withdraw `C0001` consent, then activate. The execution-time consent lookup returns NO-GO. (If `C0001` is not in a customized audience, withdraw an ID shown in persisted audience data.)

**6:30–8:00** Run forbidden-field, forbidden-network and escalation scenarios. Show backend governance denials, not merely UI labels. Then revoke a displayed grant and discuss actor/task binding, cumulative budget and replay state.

**8:00–9:00** Run audience mutation and timeout scenarios. Show digest mismatch rejection, durable `unknown` outcome and duplicate retry returning the existing intent rather than sending blindly.

**9:00–10:00** Review the model card and threat model. If a verified OpenShell environment exists, switch to real mode and show the evidence file and actual sandbox validation output. Otherwise explicitly report real sandbox tests **not run**.
