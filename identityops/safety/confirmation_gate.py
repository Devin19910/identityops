"""Makes it structurally hard to run a destructive action by accident.

This isn't a UI nicety bolted onto the CLI — it's the actual call path. Every
mutating operation in lifecycle/ and governance/ routes through `ConfirmationGate.run`,
so there is no code path that mutates a tenant without either being explicitly
dry-run or explicitly confirmed and logged.
"""
from __future__ import annotations

from typing import Callable, TypeVar

from identityops.safety.audit_log import AuditLog

T = TypeVar("T")


class ConfirmationRequiredError(Exception):
    """Raised when a mutating action is attempted without dry_run or explicit confirmation."""


class ConfirmationGate:
    def __init__(self, audit_log: AuditLog, actor: str = "unknown") -> None:
        self.audit_log = audit_log
        self.actor = actor

    def run(
        self, *, action: str, target: str, dry_run: bool, confirmed: bool,
        mutate_fn: Callable[[], T], before: dict | None = None, after: dict | None = None,
    ) -> T | None:
        if dry_run:
            self.audit_log.record(
                actor=self.actor, action=action, target=target,
                dry_run=True, before=before, after=after, success=True,
            )
            return None

        if not confirmed:
            raise ConfirmationRequiredError(
                f"Refusing to run '{action}' on '{target}' without explicit confirmation. "
                f"Re-run with --dry-run first to preview, then --confirm to execute."
            )

        try:
            result = mutate_fn()
        except Exception:
            self.audit_log.record(
                actor=self.actor, action=action, target=target,
                dry_run=False, before=before, after=after, success=False,
            )
            raise

        self.audit_log.record(
            actor=self.actor, action=action, target=target,
            dry_run=False, before=before, after=after, success=True,
        )
        return result
