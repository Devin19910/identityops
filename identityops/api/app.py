"""FastAPI app exposing the same governance checks as the CLI, for the docker-compose demo."""
from __future__ import annotations

from fastapi import FastAPI

from identityops.connectors.demo_connector import DemoConnector
from identityops.governance.consent_reviewer import ConsentReviewer
from identityops.governance.orphaned_access_scanner import OrphanedAccessScanner
from identityops.safety.audit_log import AuditLog
from identityops.safety.confirmation_gate import ConfirmationGate

app = FastAPI(title="IdentityOps (demo mode)")

_connector = DemoConnector()
_gate = ConfirmationGate(AuditLog(), actor="api-demo")


@app.get("/")
def root():
    return {
        "service": "identityops",
        "mode": "demo",
        "endpoints": ["/audit/orphaned-access", "/consent/pending"],
    }


@app.get("/audit/orphaned-access")
def orphaned_access():
    findings = OrphanedAccessScanner(_connector).scan()
    return {"count": len(findings), "findings": [f.__dict__ for f in findings]}


@app.get("/consent/pending")
def consent_pending():
    decisions = ConsentReviewer(_connector, _gate).review_all(dry_run=True, confirmed=False)
    return {
        "decisions": [
            {
                "app": d.request.app_display_name,
                "risk": d.risk_level.value,
                "auto_approved": d.auto_approved,
                "flagged_scopes": d.flagged_scopes,
            }
            for d in decisions
        ]
    }
