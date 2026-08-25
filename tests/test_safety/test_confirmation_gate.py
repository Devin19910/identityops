import pytest

from identityops.safety.audit_log import AuditLog
from identityops.safety.confirmation_gate import ConfirmationGate, ConfirmationRequiredError


def test_dry_run_never_calls_mutate_fn(tmp_path):
    gate = ConfirmationGate(AuditLog(tmp_path / "audit.jsonl"), actor="test")
    called = []

    gate.run(
        action="delete_thing", target="thing-1", dry_run=True, confirmed=False,
        mutate_fn=lambda: called.append(True),
    )

    assert called == []


def test_unconfirmed_mutation_raises(tmp_path):
    gate = ConfirmationGate(AuditLog(tmp_path / "audit.jsonl"), actor="test")

    with pytest.raises(ConfirmationRequiredError):
        gate.run(
            action="delete_thing", target="thing-1", dry_run=False, confirmed=False,
            mutate_fn=lambda: None,
        )


def test_confirmed_mutation_runs_and_logs(tmp_path):
    audit_path = tmp_path / "audit.jsonl"
    gate = ConfirmationGate(AuditLog(audit_path), actor="test")
    called = []

    gate.run(
        action="delete_thing", target="thing-1", dry_run=False, confirmed=True,
        mutate_fn=lambda: called.append(True),
    )

    assert called == [True]
    entries = AuditLog(audit_path).read_all()
    assert len(entries) == 1
    assert entries[0].success is True
    assert entries[0].dry_run is False
