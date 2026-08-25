"""Connector interface every backend (Graph, Exchange Online, demo, future Okta) implements.

Keeping this abstract is what makes the governance and lifecycle layers tenant-agnostic —
none of that code should ever import a concrete connector directly.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from identityops.models import ConsentRequest, MailboxPermission, User


class TenantConnector(ABC):
    """Minimal surface area needed by the lifecycle and governance layers."""

    @abstractmethod
    def list_users(self) -> list[User]: ...

    @abstractmethod
    def list_shared_mailboxes(self) -> list[str]: ...

    @abstractmethod
    def get_mailbox_permissions(self, mailbox: str) -> list[MailboxPermission]: ...

    @abstractmethod
    def remove_mailbox_permission(self, mailbox: str, trustee_upn: str, access_right: str) -> None: ...

    @abstractmethod
    def list_pending_consent_requests(self) -> list[ConsentRequest]: ...

    @abstractmethod
    def grant_tenant_consent(self, app_id: str, scopes: list[str]) -> None: ...

    @abstractmethod
    def disable_user(self, upn: str) -> None: ...

    @abstractmethod
    def revoke_sessions(self, upn: str) -> None: ...
