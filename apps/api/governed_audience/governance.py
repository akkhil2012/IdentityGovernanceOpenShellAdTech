from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone

from .db import GrantState
from .models import Grant, SignedGrant


class GovernanceDenied(ValueError):
    pass


class GovernanceService:
    """Trusted service boundary. Workers receive grants but cannot mint them."""

    def __init__(self, key: str, policy_version: str):
        self.key = key.encode()
        self.policy_version = policy_version

    @staticmethod
    def _canonical(claims: Grant) -> bytes:
        return json.dumps(claims.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode()

    def _sign(self, claims: Grant) -> str:
        return hmac.new(self.key, self._canonical(claims), hashlib.sha256).hexdigest()

    def mint(self, *, subject: str, task: str, purpose: str, capabilities: list[str], resources: list[str], destinations: list[str], record_budget: int, actor: str, parent: SignedGrant | None = None, on_behalf_of: str = "Fabio") -> SignedGrant:
        if parent:
            p = parent.claims
            if not set(capabilities) <= set(p.capabilities) or not set(resources) <= set(p.resources) or not set(destinations) <= set(p.destinations):
                raise GovernanceDenied("delegated authority exceeds parent scope")
            if record_budget > p.record_budget or task != p.task or purpose != p.purpose:
                raise GovernanceDenied("delegation exceeds task, purpose, or budget")
        claims = Grant(
            grant_id=f"g-{secrets.token_hex(8)}", subject=subject,
            root_subject=parent.claims.root_subject if parent else subject,
            parent_grant=parent.claims.grant_id if parent else None,
            task=task, purpose=purpose, capabilities=capabilities, resources=resources,
            destinations=destinations, record_budget=record_budget,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            policy_version=self.policy_version, actor=actor, nonce=secrets.token_hex(12),
            on_behalf_of=on_behalf_of,
        )
        return SignedGrant(claims=claims, signature=self._sign(claims))

    def validate(self, db, signed: SignedGrant, *, actor: str, task: str, capability: str, resource: str, destination: str, records: int, nonce: str | None = None) -> None:
        c = signed.claims
        if not hmac.compare_digest(self._sign(c), signed.signature):
            raise GovernanceDenied("invalid signature")
        if c.issuer != "governance-service" or c.audience != "task-broker":
            raise GovernanceDenied("invalid issuer or audience")
        if c.actor != actor or c.task != task:
            raise GovernanceDenied("actor or task binding mismatch")
        expires = c.expires_at if c.expires_at.tzinfo else c.expires_at.replace(tzinfo=timezone.utc)
        if expires <= datetime.now(timezone.utc) or c.policy_version != self.policy_version:
            raise GovernanceDenied("expired or obsolete policy")
        if capability not in c.capabilities or resource not in c.resources or destination not in c.destinations:
            raise GovernanceDenied("capability, resource, or destination denied")
        state = db.get(GrantState, c.grant_id)
        if state is None:
            state = GrantState(grant_id=c.grant_id, revoked=False, consumed_records=0, seen_nonces_json="[]")
            db.add(state)
        if state.revoked:
            raise GovernanceDenied("grant revoked")
        seen = set(json.loads(state.seen_nonces_json))
        use_nonce = nonce or c.nonce
        if use_nonce in seen:
            raise GovernanceDenied("replay detected")
        if state.consumed_records + records > c.record_budget:
            raise GovernanceDenied("cumulative record budget exceeded")
        seen.add(use_nonce)
        state.seen_nonces_json = json.dumps(sorted(seen))
        state.consumed_records += records
        db.commit()

    @staticmethod
    def revoke(db, grant_id: str) -> bool:
        state = db.get(GrantState, grant_id)
        if state is None:
            state = GrantState(grant_id=grant_id, revoked=True, consumed_records=0, seen_nonces_json="[]")
            db.add(state)
        else:
            state.revoked = True
        db.commit()
        return True
