"""CLI entrypoint. Defaults to the demo connector so `identityops audit orphaned-access`
works immediately after install, with zero configuration."""
from __future__ import annotations

import os

import typer
from rich.console import Console
from rich.table import Table

from identityops.connectors.demo_connector import DemoConnector
from identityops.governance.consent_reviewer import ConsentReviewer
from identityops.governance.orphaned_access_scanner import OrphanedAccessScanner
from identityops.lifecycle.offboarding import OffboardingWorkflow
from identityops.safety.audit_log import AuditLog
from identityops.safety.confirmation_gate import ConfirmationGate, ConfirmationRequiredError

app = typer.Typer(help="IdentityOps — identity lifecycle automation with a governance layer.")
audit_app = typer.Typer(help="Governance/audit commands.")
consent_app = typer.Typer(help="OAuth consent review commands.")
app.add_typer(audit_app, name="audit")
app.add_typer(consent_app, name="consent")

console = Console()


def _get_connector():
    # Real usage: set IDENTITYOPS_TENANT_ID/CLIENT_ID/CLIENT_SECRET and swap in GraphConnector/ExoConnector.
    if os.environ.get("IDENTITYOPS_TENANT_ID"):
        raise typer.Exit("Real-tenant wiring is intentionally left as an exercise — see docs/architecture.md")
    return DemoConnector()


@audit_app.command("orphaned-access")
def audit_orphaned_access(remediate: bool = False, confirm: bool = False) -> None:
    """Scan all shared mailboxes for permissions held by disabled/departed users."""
    connector = _get_connector()
    scanner = OrphanedAccessScanner(connector)
    findings = scanner.scan()

    if not findings:
        console.print("[green]No orphaned access found.[/green]")
        return

    table = Table(title="Orphaned Mailbox Access")
    table.add_column("Mailbox")
    table.add_column("Trustee")
    table.add_column("Rights")
    table.add_column("Reason")
    for f in findings:
        table.add_row(f.mailbox, f.trustee_upn, ", ".join(f.access_rights), f.reason)
    console.print(table)

    if remediate:
        gate = ConfirmationGate(AuditLog(), actor="cli")
        try:
            scanner.remediate(findings, dry_run=not confirm, confirmed=confirm, gate=gate)
            if confirm:
                console.print("[yellow]Remediated all findings above.[/yellow]")
            else:
                console.print("[dim]Dry run only — re-run with --remediate --confirm to actually remove access.[/dim]")
        except ConfirmationRequiredError as e:
            console.print(f"[red]{e}[/red]")


@consent_app.command("review")
def consent_review(confirm: bool = False) -> None:
    """Triage pending OAuth consent requests — auto-approve low risk, flag the rest."""
    connector = _get_connector()
    gate = ConfirmationGate(AuditLog(), actor="cli")
    reviewer = ConsentReviewer(connector, gate)
    decisions = reviewer.review_all(dry_run=not confirm, confirmed=confirm)

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


@app.command()
def offboard(upn: str, confirm: bool = False) -> None:
    """Block sign-in and revoke sessions for a departing user."""
    connector = _get_connector()
    gate = ConfirmationGate(AuditLog(), actor="cli")
    workflow = OffboardingWorkflow(connector, gate)
    try:
        workflow.block_signin(upn, dry_run=not confirm, confirmed=confirm)
        console.print(f"[green]Offboarding step complete for {upn}[/green]" if confirm
                       else f"[dim]Dry run for {upn} — re-run with --confirm to execute[/dim]")
    except ConfirmationRequiredError as e:
        console.print(f"[red]{e}[/red]")


if __name__ == "__main__":
    app()
