"""Regression test for a real bug caught while building this: each CLI invocation
is a separate process, so without persistence, remediating a finding and then
re-scanning in the next command would silently 'undo' the fix by reloading the
original seed data. This proves state actually survives across instances."""
from identityops.connectors.demo_connector import DemoConnector
from identityops.governance.orphaned_access_scanner import OrphanedAccessScanner
from identityops.safety.audit_log import AuditLog
from identityops.safety.confirmation_gate import ConfirmationGate


def test_remediation_persists_across_separate_connector_instances(tmp_path):
    state_path = tmp_path / "state.json"
    audit = AuditLog(tmp_path / "audit.jsonl")
    gate = ConfirmationGate(audit, actor="test")

    # First "process": scan and remediate.
    connector_1 = DemoConnector(state_path=state_path)
    scanner_1 = OrphanedAccessScanner(connector_1)
    findings = scanner_1.scan()
    assert len(findings) == 2
    scanner_1.remediate(findings, dry_run=False, confirmed=True, gate=gate)

    # Second "process": a brand-new DemoConnector instance, same state file.
    connector_2 = DemoConnector(state_path=state_path)
    scanner_2 = OrphanedAccessScanner(connector_2)
    assert scanner_2.scan() == []
