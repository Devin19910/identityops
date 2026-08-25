"""Orchestrates offboarding through the state machine, safety gate, and audit log."""
from __future__ import annotations

from identityops.connectors.base import TenantConnector
from identityops.lifecycle.state_machine import OffboardingStateMachine
from identityops.models import OffboardingState
from identityops.safety.confirmation_gate import ConfirmationGate


class OffboardingWorkflow:
    def __init__(self, connector: TenantConnector, gate: ConfirmationGate) -> None:
        self.connector = connector
        self.gate = gate
        self.machine = OffboardingStateMachine()

    def block_signin(self, upn: str, *, dry_run: bool, confirmed: bool) -> None:
        self.gate.run(
            action="disable_user", target=upn, dry_run=dry_run, confirmed=confirmed,
            mutate_fn=lambda: self.connector.disable_user(upn),
            before={"enabled": True}, after={"enabled": False},
        )
        self.gate.run(
            action="revoke_sessions", target=upn, dry_run=dry_run, confirmed=confirmed,
            mutate_fn=lambda: self.connector.revoke_sessions(upn),
        )
        if not dry_run and confirmed:
            self.machine.transition(OffboardingState.BLOCKED)

    # forwarding/scheduled-delete steps follow the same gate.run(...) pattern —
    # omitted here for brevity, see tests/test_lifecycle for the full sequence.
