"""Fail-closed adapter for an explicitly allowlisted protected operation.

This module is not an HTTP server or identity provider. Only a trusted ingress
may supply the principal, action, rate subject, and approval verifier.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, TypeVar

from security.max_security import MaxSecurityEngine, SecurityDenied

T = TypeVar("T")


@dataclass(frozen=True)
class ActionPolicy:
    """By default every action requires independently verified operator approval."""
    requires_approval: bool = True


class ProtectedOperationGateway:
    """Execute a caller-supplied operation only after all applicable gates pass.

    The gateway cannot prove the request's principal; an authenticated ingress
    must derive it from a verified identity. Approval verification must bind
    principal, action, request digest, and a single-use approval artifact.
    """

    def __init__(
        self,
        engine: MaxSecurityEngine,
        policies: Mapping[str, ActionPolicy],
        approval_verifier: Callable[[str, str, bytes, object], bool] | None = None,
    ):
        self.engine = engine
        self.policies = dict(policies)
        self.approval_verifier = approval_verifier

    def execute(
        self,
        *,
        action: str,
        principal: str,
        rate_subject: str,
        token: str,
        signature: str,
        method: str,
        path: str,
        timestamp: int,
        nonce: str,
        body: bytes,
        operation: Callable[[str], T],
        approval: object = None,
        now: int | None = None,
    ) -> T:
        """Run a trusted callback only after policy, approval and engine gates.

        Unknown actions, unavailable verification, and exceptions deny execution.
        This does not provide an outbox, payment idempotency, or external approval
        storage. Never attach live side effects without those independent controls.
        """
        if not isinstance(action, str) or action not in self.policies:
            raise SecurityDenied("action not allowlisted")
        if not callable(operation):
            raise SecurityDenied("operation callback unavailable")
        policy = self.policies[action]
        if not isinstance(policy, ActionPolicy):
            raise SecurityDenied("invalid action policy")
        if policy.requires_approval and self.approval_verifier is None:
            raise SecurityDenied("independent approval verifier unavailable")
        # Only the engine invokes this callback, after authentication, replay,
        # rate limiting, and permission checks have all succeeded.
        approval_check = (
            (lambda: self.approval_verifier(principal, action, body, approval))
            if policy.requires_approval else None
        )
        receipt = self.engine.authorize_operation(
            token=token,
            signature=signature,
            method=method,
            path=path,
            timestamp=timestamp,
            nonce=nonce,
            body=body,
            principal=principal,
            action=action,
            rate_subject=rate_subject,
            now=now,
            approval_check=approval_check,
        )
        return operation(receipt)
