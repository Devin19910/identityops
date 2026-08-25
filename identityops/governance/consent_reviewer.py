"""Triages pending OAuth consent requests so a human only has to look at the risky ones."""
from __future__ import annotations

from identityops.connectors.base import TenantConnector
from identityops.governance.risk_rules import classify_scopes
from identityops.models import ConsentDecision, RiskLevel
from identityops.safety.confirmation_gate import ConfirmationGate


class ConsentReviewer:
    def __init__(self, connector: TenantConnector, gate: ConfirmationGate) -> None:
        self.connector = connector
        self.gate = gate

    def review_all(self, *, dry_run: bool = True, confirmed: bool = False) -> list[ConsentDecision]:
        decisions: list[ConsentDecision] = []
        for req in self.connector.list_pending_consent_requests():
            risk, flagged = classify_scopes(req.scopes)

            if risk == RiskLevel.LOW:
                self.gate.run(
                    action="auto_approve_consent",
                    target=req.app_display_name,
                    dry_run=dry_run,
                    confirmed=confirmed,
                    mutate_fn=lambda r=req: self.connector.grant_tenant_consent(r.id, r.scopes),
                    before={"scopes": req.scopes},
                    after={"status": "approved"},
                )
                decisions.append(ConsentDecision(request=req, risk_level=risk, auto_approved=True))
            else:
                # Medium/high risk is never auto-approved — it's surfaced for a human decision.
                decisions.append(
                    ConsentDecision(request=req, risk_level=risk, auto_approved=False, flagged_scopes=flagged)
                )

        return decisions
