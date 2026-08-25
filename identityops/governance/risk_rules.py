"""Declarative scope risk classification.

Kept as plain data, not buried in if/else branches, so the policy is easy to
audit and easy to extend (see the roadmap item on a YAML-defined DSL — this
module is the seam where that would plug in).
"""
from __future__ import annotations

from identityops.models import RiskLevel

# Scopes that are read-only, identity-only, or otherwise low-blast-radius.
SAFE_SCOPES: set[str] = {
    "openid", "profile", "offline_access", "email",
    "User.Read", "User.ReadBasic.All",
    "Calendars.Read", "Team.ReadBasic.All", "Channel.ReadBasic.All",
}

# Scopes that grant write/delete access to mail, files, or directory-wide data.
HIGH_RISK_SCOPES: set[str] = {
    "Mail.ReadWrite", "Mail.ReadWrite.Shared", "Mail.Send", "Mail.Send.Shared",
    "MailboxSettings.ReadWrite",
    "Directory.ReadWrite.All", "User.ReadWrite.All",
    "Files.ReadWrite.All", "Sites.FullControl.All",
    "Chat.ReadWrite.All", "AppCatalog.ReadWrite.All",
}


def classify_scopes(scopes: list[str]) -> tuple[RiskLevel, list[str]]:
    """Returns the overall risk level and the specific scopes that triggered it."""
    flagged = [s for s in scopes if s in HIGH_RISK_SCOPES]
    if flagged:
        return RiskLevel.HIGH, flagged

    unknown = [s for s in scopes if s not in SAFE_SCOPES]
    if unknown:
        return RiskLevel.MEDIUM, unknown

    return RiskLevel.LOW, []
