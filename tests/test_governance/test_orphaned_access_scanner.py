from identityops.connectors.demo_connector import DemoConnector
from identityops.governance.orphaned_access_scanner import OrphanedAccessScanner


def test_scan_finds_disabled_user_access(tmp_path):
    scanner = OrphanedAccessScanner(DemoConnector(state_path=tmp_path / "state.json"))
    findings = scanner.scan()

    trustees = {f.trustee_upn for f in findings}
    assert "sam.okafor@demo.local" in trustees  # planted disabled-user finding

    # Active users' legitimate access must not be flagged.
    assert "alex.rivera@demo.local" not in trustees
    assert "jamie.chen@demo.local" not in trustees


def test_scan_catches_finding_across_multiple_mailboxes(tmp_path):
    scanner = OrphanedAccessScanner(DemoConnector(state_path=tmp_path / "state.json"))
    findings = scanner.scan()

    mailboxes_with_sam = {f.mailbox for f in findings if f.trustee_upn == "sam.okafor@demo.local"}
    assert mailboxes_with_sam == {"support@demo.local", "billing@demo.local"}
