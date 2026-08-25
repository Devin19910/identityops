"""Exchange Online connector — mailbox permissions live here, not in Graph.

This is a deliberate design choice, not an oversight: Graph has no API for
FullAccess/SendAs mailbox delegation. Any tool that only talks to Graph will
structurally miss the orphaned-access class of bug this project exists to catch.
Uses the EXO REST InvokeCommand endpoint under app-only auth (Exchange.ManageAsApp).
"""
from __future__ import annotations

import os

import httpx

from identityops.models import MailboxPermission


class ExoConnector:
    def __init__(self) -> None:
        self.tenant_id = os.environ["IDENTITYOPS_TENANT_ID"]
        self.client_id = os.environ["IDENTITYOPS_CLIENT_ID"]
        self.client_secret = os.environ["IDENTITYOPS_CLIENT_SECRET"]
        self._token: str | None = None

    def _get_token(self) -> str:
        if self._token:
            return self._token
        resp = httpx.post(
            f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "https://outlook.office.com/.default",
            },
            timeout=15,
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        return self._token

    def _invoke(self, cmdlet: str, params: dict) -> dict:
        resp = httpx.post(
            f"https://outlook.office.com/adminapi/beta/{self.tenant_id}/InvokeCommand",
            headers={"Authorization": f"Bearer {self._get_token()}", "Content-Type": "application/json"},
            json={"CmdletInput": {"CmdletName": cmdlet, "Parameters": params}},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()

    def list_shared_mailboxes(self) -> list[str]:
        result = self._invoke("Get-Mailbox", {"RecipientTypeDetails": "SharedMailbox", "ResultSize": "Unlimited"})
        return [m["PrimarySmtpAddress"] for m in result.get("value", [])]

    def get_mailbox_permissions(self, mailbox: str) -> list[MailboxPermission]:
        perms: list[MailboxPermission] = []
        full = self._invoke("Get-MailboxPermission", {"Identity": mailbox})
        for p in full.get("value", []):
            trustee = str(p.get("User", ""))
            if "SELF" in trustee.upper() or not p.get("AccessRights"):
                continue
            perms.append(MailboxPermission(mailbox, trustee, list(p["AccessRights"])))

        send_as = self._invoke("Get-RecipientPermission", {"Identity": mailbox})
        for p in send_as.get("value", []):
            trustee = str(p.get("Trustee", ""))
            if "SELF" in trustee.upper():
                continue
            perms.append(MailboxPermission(mailbox, trustee, ["SendAs"]))

        return perms

    def remove_mailbox_permission(self, mailbox: str, trustee_upn: str, access_right: str) -> None:
        if access_right == "SendAs":
            self._invoke("Remove-RecipientPermission", {
                "Identity": mailbox, "Trustee": trustee_upn, "AccessRights": "SendAs", "Confirm": False,
            })
        else:
            self._invoke("Remove-MailboxPermission", {
                "Identity": mailbox, "User": trustee_upn, "AccessRights": access_right, "Confirm": False,
            })
