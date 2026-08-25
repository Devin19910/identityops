"""Finds direct mailbox permissions held by users who are no longer active.

This is the check that group-based offboarding structurally cannot perform:
FullAccess and SendAs grants are per-mailbox delegations, not group memberships,
so removing someone from every security group in the tenant does nothing to them.
"""
from __future__ import annotations

from identityops.connectors.base import TenantConnector
from identityops.models import OrphanedAccessFinding


class OrphanedAccessScanner:
    def __init__(self, connector: TenantConnector) -> None:
        self.connector = connector

    def scan(self) -> list[OrphanedAccessFinding]:
        users_by_upn = {u.upn: u for u in self.connector.list_users()}
        findings: list[OrphanedAccessFinding] = []

        for mailbox in self.connector.list_shared_mailboxes():
            for perm in self.connector.get_mailbox_permissions(mailbox):
                user = users_by_upn.get(perm.trustee_upn)

                if user is None:
                    reason = "trustee not found in directory (likely fully deleted)"
                elif not user.enabled:
                    reason = "trustee account is disabled"
                else:
                    continue

                findings.append(
                    OrphanedAccessFinding(
                        mailbox=mailbox,
                        trustee_upn=perm.trustee_upn,
                        access_rights=perm.access_rights,
                        reason=reason,
                    )
                )

        return findings

    def remediate(
        self, findings: list[OrphanedAccessFinding], *, dry_run: bool, confirmed: bool, gate,
    ) -> None:
        for finding in findings:
            for right in finding.access_rights:
                gate.run(
                    action="remove_orphaned_mailbox_permission",
                    target=f"{finding.mailbox} <- {finding.trustee_upn} ({right})",
                    dry_run=dry_run,
                    confirmed=confirmed,
                    mutate_fn=lambda m=finding.mailbox, t=finding.trustee_upn, r=right: (
                        self.connector.remove_mailbox_permission(m, t, r)
                    ),
                    before={"access_rights": finding.access_rights},
                    after={"access_rights": []},
                )
