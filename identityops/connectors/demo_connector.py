"""In-memory fake tenant — lets anyone run the full tool with zero real credentials.

The planted data here deliberately reproduces two real-world scenarios:
  1. A departed user (disabled, no active groups) who still holds SendAs on a
     shared mailbox — the exact gap group-based offboarding misses.
  2. A mix of low-risk and high-risk pending OAuth consent requests.

State persists to a local JSON file between CLI invocations (each command is a
separate process, so without this, "remediate" in one command and "re-scan" in
the next would each start from a fresh fixture and the fix would never appear to
stick). Delete the state file to reset the demo to its original planted state.
"""
from __future__ import annotations

import json
from pathlib import Path

from identityops.connectors.base import TenantConnector
from identityops.models import ConsentRequest, MailboxPermission, User

DEFAULT_STATE_PATH = Path(".identityops_demo_state.json")

_SEED_USERS = [
    {"id": "u1", "upn": "alex.rivera@demo.local", "display_name": "Alex Rivera", "enabled": True, "department": "Engineering"},
    {"id": "u2", "upn": "jamie.chen@demo.local", "display_name": "Jamie Chen", "enabled": True, "department": "Sales"},
    {"id": "u3", "upn": "sam.okafor@demo.local", "display_name": "Sam Okafor", "enabled": False, "department": "Consulting"},
    {"id": "u4", "upn": "taylor.morgan@demo.local", "display_name": "Taylor Morgan", "enabled": True, "department": "Finance"},
]

_SEED_MAILBOX_PERMISSIONS = {
    "support@demo.local": [
        {"trustee_upn": "alex.rivera@demo.local", "access_rights": ["FullAccess"]},
        {"trustee_upn": "jamie.chen@demo.local", "access_rights": ["SendAs"]},
        # Planted finding: sam.okafor is disabled but still has SendAs here.
        {"trustee_upn": "sam.okafor@demo.local", "access_rights": ["SendAs"]},
    ],
    "billing@demo.local": [
        {"trustee_upn": "taylor.morgan@demo.local", "access_rights": ["FullAccess", "SendAs"]},
        # Second planted finding: same disabled user, different mailbox.
        {"trustee_upn": "sam.okafor@demo.local", "access_rights": ["FullAccess"]},
    ],
}

_SEED_CONSENT_REQUESTS = [
    {"id": "c1", "app_display_name": "Standup Bot", "requested_by_upn": "jamie.chen@demo.local",
     "scopes": ["openid", "profile", "User.Read"]},
    {"id": "c2", "app_display_name": "Inbox Miner Pro", "requested_by_upn": "taylor.morgan@demo.local",
     "scopes": ["Mail.ReadWrite", "MailboxSettings.ReadWrite", "offline_access"]},
    {"id": "c3", "app_display_name": "Calendar Sync", "requested_by_upn": "alex.rivera@demo.local",
     "scopes": ["Calendars.Read", "openid", "profile"]},
]


class DemoConnector(TenantConnector):
    def __init__(self, state_path: Path = DEFAULT_STATE_PATH) -> None:
        self.state_path = state_path
        if state_path.exists():
            state = json.loads(state_path.read_text())
        else:
            state = {
                "users": _SEED_USERS,
                "mailbox_permissions": _SEED_MAILBOX_PERMISSIONS,
                "consent_requests": _SEED_CONSENT_REQUESTS,
            }

        self._users = [User(**u) for u in state["users"]]
        self._mailbox_permissions: dict[str, list[MailboxPermission]] = {
            mailbox: [MailboxPermission(mailbox, p["trustee_upn"], list(p["access_rights"])) for p in perms]
            for mailbox, perms in state["mailbox_permissions"].items()
        }
        self._consent_requests = [ConsentRequest(**c) for c in state["consent_requests"]]

    def _save(self) -> None:
        state = {
            "users": [u.__dict__ for u in self._users],
            "mailbox_permissions": {
                mailbox: [{"trustee_upn": p.trustee_upn, "access_rights": p.access_rights} for p in perms]
                for mailbox, perms in self._mailbox_permissions.items()
            },
            "consent_requests": [c.__dict__ for c in self._consent_requests],
        }
        self.state_path.write_text(json.dumps(state, indent=2))

    def list_users(self) -> list[User]:
        return list(self._users)

    def list_shared_mailboxes(self) -> list[str]:
        return list(self._mailbox_permissions.keys())

    def get_mailbox_permissions(self, mailbox: str) -> list[MailboxPermission]:
        return list(self._mailbox_permissions.get(mailbox, []))

    def remove_mailbox_permission(self, mailbox: str, trustee_upn: str, access_right: str) -> None:
        perms = self._mailbox_permissions.get(mailbox, [])
        for p in perms:
            if p.trustee_upn == trustee_upn and access_right in p.access_rights:
                p.access_rights.remove(access_right)
        self._mailbox_permissions[mailbox] = [p for p in perms if p.access_rights]
        self._save()

    def list_pending_consent_requests(self) -> list[ConsentRequest]:
        return list(self._consent_requests)

    def grant_tenant_consent(self, app_id: str, scopes: list[str]) -> None:
        self._consent_requests = [c for c in self._consent_requests if c.id != app_id]
        self._save()

    def disable_user(self, upn: str) -> None:
        for u in self._users:
            if u.upn == upn:
                u.enabled = False
        self._save()

    def revoke_sessions(self, upn: str) -> None:
        # Demo tenant has no session concept to mutate — real connectors call the
        # actual revoke-sessions API here. Nothing to persist for the fake backend.
        pass
