"""Regenerates the terminal screenshots used in the README.

These are real captured output from the actual CLI logic (via rich's SVG
export), not hand-drawn mockups — run this after any UI-affecting change:

    python scripts/generate_screenshots.py
"""
from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.table import Table

from identityops.connectors.demo_connector import DemoConnector
from identityops.governance.consent_reviewer import ConsentReviewer
from identityops.governance.orphaned_access_scanner import OrphanedAccessScanner
from identityops.safety.audit_log import AuditLog
from identityops.safety.confirmation_gate import ConfirmationGate

OUT_DIR = Path(__file__).parent.parent / "docs" / "screenshots"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TERMINAL_THEME_ARGS = dict(
    background_color="#0d1117",
    theme=None,
)


def screenshot_orphaned_access() -> None:
    console = Console(record=True, width=104)
    console.print("[bold]$[/bold] identityops audit orphaned-access", style="bright_black")
    console.print()

    connector = DemoConnector(state_path=Path("/tmp/identityops_screenshot_state.json"))
    if connector.state_path.exists():
        connector.state_path.unlink()
    connector = DemoConnector(state_path=Path("/tmp/identityops_screenshot_state.json"))

    findings = OrphanedAccessScanner(connector).scan()
    table = Table(title="Orphaned Mailbox Access")
    table.add_column("Mailbox")
    table.add_column("Trustee")
    table.add_column("Rights")
    table.add_column("Reason")
    for f in findings:
        table.add_row(f.mailbox, f.trustee_upn, ", ".join(f.access_rights), f.reason)
    console.print(table)

    console.save_svg(str(OUT_DIR / "audit-orphaned-access.svg"), title="identityops")
    connector.state_path.unlink(missing_ok=True)


def screenshot_consent_review() -> None:
    console = Console(record=True, width=104)
    console.print("[bold]$[/bold] identityops consent review", style="bright_black")
    console.print()

    connector = DemoConnector(state_path=Path("/tmp/identityops_screenshot_consent_state.json"))
    connector.state_path.unlink(missing_ok=True)
    connector = DemoConnector(state_path=Path("/tmp/identityops_screenshot_consent_state.json"))

    gate = ConfirmationGate(AuditLog(Path("/tmp/identityops_screenshot_audit.jsonl")), actor="demo")
    decisions = ConsentReviewer(connector, gate).review_all(dry_run=True, confirmed=False)

    table = Table(title="Consent Review")
    table.add_column("App")
    table.add_column("Risk")
    table.add_column("Decision")
    table.add_column("Flagged scopes")
    for d in decisions:
        decision = "auto-approved" if d.auto_approved else "ESCALATED — needs human review"
        style = "green" if d.auto_approved else "red"
        table.add_row(
            d.request.app_display_name, d.risk_level.value,
            f"[{style}]{decision}[/{style}]", ", ".join(d.flagged_scopes) or "-",
        )
    console.print(table)

    console.save_svg(str(OUT_DIR / "consent-review.svg"), title="identityops")
    connector.state_path.unlink(missing_ok=True)
    Path("/tmp/identityops_screenshot_audit.jsonl").unlink(missing_ok=True)


if __name__ == "__main__":
    screenshot_orphaned_access()
    screenshot_consent_review()
    print(f"Wrote screenshots to {OUT_DIR}")
