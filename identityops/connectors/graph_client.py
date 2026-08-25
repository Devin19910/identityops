"""Microsoft Graph connector — app-only client-credentials auth.

Requires an Azure AD app registration with, at minimum:
  User.Read.All, Directory.ReadWrite.All (application permissions, admin-consented)

Set via environment variables: IDENTITYOPS_TENANT_ID, IDENTITYOPS_CLIENT_ID,
IDENTITYOPS_CLIENT_SECRET. Never hardcode these — this module reads them from
the environment only, and nothing in this repo ships with real credentials.
"""
from __future__ import annotations

import os

import httpx

from identityops.connectors.base import TenantConnector
from identityops.models import ConsentRequest, MailboxPermission, User

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class GraphConnector(TenantConnector):
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
                "scope": "https://graph.microsoft.com/.default",
            },
            timeout=15,
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        return self._token

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._get_token()}"}

    def list_users(self) -> list[User]:
        resp = httpx.get(
            f"{GRAPH_BASE}/users",
            headers=self._headers(),
            params={"$select": "id,userPrincipalName,displayName,accountEnabled,department", "$top": "999"},
            timeout=30,
        )
        resp.raise_for_status()
        return [
            User(
                id=u["id"], upn=u["userPrincipalName"], display_name=u["displayName"],
                enabled=u["accountEnabled"], department=u.get("department"),
            )
            for u in resp.json().get("value", [])
        ]

    def disable_user(self, upn: str) -> None:
        resp = httpx.patch(
            f"{GRAPH_BASE}/users/{upn}",
            headers=self._headers(),
            json={"accountEnabled": False},
            timeout=15,
        )
        resp.raise_for_status()

    def revoke_sessions(self, upn: str) -> None:
        resp = httpx.post(
            f"{GRAPH_BASE}/users/{upn}/revokeSignInSessions",
            headers=self._headers(),
            timeout=15,
        )
        resp.raise_for_status()

    def list_pending_consent_requests(self) -> list[ConsentRequest]:
        resp = httpx.get(
            f"{GRAPH_BASE}/identityGovernance/appConsent/appConsentRequests",
            headers={**self._headers(), "ConsistencyLevel": "eventual"},
            params={"$filter": "userConsentRequests/any(u:u/status eq 'InProgress')"},
            timeout=30,
        )
        resp.raise_for_status()
        return [
            ConsentRequest(
                id=r["id"], app_display_name=r["appDisplayName"],
                requested_by_upn=(r.get("userConsentRequests") or [{}])[0].get("reason", "unknown"),
                scopes=[s["displayName"] for s in r.get("pendingScopes", [])],
            )
            for r in resp.json().get("value", [])
        ]

    def grant_tenant_consent(self, app_id: str, scopes: list[str]) -> None:
        # Requires the app's servicePrincipal to exist first (create if missing),
        # then an oauth2PermissionGrants POST with consentType "AllPrincipals".
        # See docs/architecture.md for the full two-step flow and why it's two calls.
        raise NotImplementedError("Wire this up against your own tenant — see docs/architecture.md")

    def list_shared_mailboxes(self) -> list[str]:
        raise NotImplementedError("Shared mailbox enumeration goes through Exchange Online — see ExoConnector")

    def get_mailbox_permissions(self, mailbox: str) -> list[MailboxPermission]:
        raise NotImplementedError("See ExoConnector.get_mailbox_permissions")

    def remove_mailbox_permission(self, mailbox: str, trustee_upn: str, access_right: str) -> None:
        raise NotImplementedError("See ExoConnector.remove_mailbox_permission")
