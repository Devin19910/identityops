"""Explicit offboarding states with enforced transitions.

An offboarding workflow implemented as a pile of sequential function calls has
no way to represent "we got partway through and stopped" — this does.
"""
from __future__ import annotations

from identityops.models import OffboardingState

_VALID_TRANSITIONS: dict[OffboardingState, set[OffboardingState]] = {
    OffboardingState.PENDING: {OffboardingState.BLOCKED},
    OffboardingState.BLOCKED: {OffboardingState.FORWARDING},
    OffboardingState.FORWARDING: {OffboardingState.SCHEDULED_DELETE},
    OffboardingState.SCHEDULED_DELETE: {OffboardingState.DELETED},
    OffboardingState.DELETED: set(),
}


class InvalidTransitionError(Exception):
    pass


class OffboardingStateMachine:
    def __init__(self, initial: OffboardingState = OffboardingState.PENDING) -> None:
        self.state = initial

    def transition(self, target: OffboardingState) -> None:
        allowed = _VALID_TRANSITIONS[self.state]
        if target not in allowed:
            raise InvalidTransitionError(
                f"Cannot go from {self.state.value} to {target.value}. "
                f"Valid next states: {[s.value for s in allowed] or 'none (terminal)'}"
            )
        self.state = target
