"""Core data models shared across connectors, governance, and lifecycle modules."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class OffboardingState(str, Enum):
    PENDING = "pending"
    BLOCKED = "blocked"
    FORWARDING = "forwarding"
    SCHEDULED_DELETE = "scheduled_delete"
    DELETED = "deleted"


@dataclass
class User:
    id: str
    upn: str
    display_name: str
    enabled: bool
    department: str | None = None


@dataclass
class MailboxPermission:
    mailbox: str
    trustee_upn: str
    access_rights: list[str]  # e.g. ["FullAccess"], ["SendAs"]


@dataclass
class OrphanedAccessFinding:
    mailbox: str
    trustee_upn: str
    access_rights: list[str]
    reason: str


@dataclass
class ConsentRequest:
    id: str
    app_display_name: str
    requested_by_upn: str
    scopes: list[str]


@dataclass
class ConsentDecision:
    request: ConsentRequest
    risk_level: RiskLevel
    auto_approved: bool
    flagged_scopes: list[str] = field(default_factory=list)


@dataclass
class AuditEntry:
    timestamp: str
    actor: str
    action: str
    target: str
    dry_run: bool
    before: dict | None
    after: dict | None
    success: bool


def now_iso() -> str:
    return datetime.now(UTC).isoformat()
