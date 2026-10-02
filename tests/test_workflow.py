def run(client, scenario="authorized_success"):
    return client.post("/api/workflows",json={"scenario":scenario,"brief":{"name":"test","request":"rank","purpose":"personalized_advertising","channel":"display","destination":"mock-dsp","max_audience":10}}).json()

def test_success_and_idempotent_activation(client):
    result=run(client); assert result["decision"]=="GO" and result["funnel"]["approved"]==10
    body={"workflow_id":result["workflow_id"],"idempotency_key":"once"}
    first=client.post("/api/activate",json=body).json(); second=client.post("/api/activate",json=body).json()
    assert first["decision"]=="GO" and first["sent"] is False
    assert second["receipt_id"]==first["receipt_id"] and second["idempotent_replay"] is True

def test_missing_consent_is_hard_no_go(client):
    assert run(client,"missing_consent")["decision"]=="NO-GO"

def test_approval_binding_rejects_mutation(client):
    result=run(client,"audience_mutation")
    receipt=client.post("/api/activate",json={"workflow_id":result["workflow_id"],"idempotency_key":"mutation"}).json()
    assert receipt["decision"]=="NO-GO" and "changed" in receipt["reason"]

def test_consent_is_fresh_at_execution(client):
    result=run(client,"consent_withdrawal")
    receipt=client.post("/api/activate",json={"workflow_id":result["workflow_id"],"idempotency_key":"withdrawn"}).json()
    assert receipt["decision"]=="NO-GO" and "consent" in receipt["reason"]

def test_policy_denials_are_backend_enforced(client):
    for scenario in ("forbidden_field","forbidden_network","capability_escalation","grant_revocation"):
        result=run(client,scenario)
        assert result["decision"]=="NO-GO" and any(x["status"]=="denied" for x in result["timeline"])

def test_unknown_outcome_is_not_retried(client):
    result=run(client,"activation_timeout")
    body={"workflow_id":result["workflow_id"],"idempotency_key":"unknown"}
    first=client.post("/api/activate",json=body).json(); retry=client.post("/api/activate",json=body).json()
    assert first["decision"]=="REVIEW" and retry["status"]=="unknown" and retry["idempotent_replay"]
