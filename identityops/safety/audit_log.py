"""Append-only audit log. Every mutating action lands here, dry-run or not."""
from __future__ import annotations

import json
from pathlib import Path

from identityops.models import AuditEntry, now_iso


class AuditLog:
    def __init__(self, path: str | Path = "identityops_audit.jsonl") -> None:
        self.path = Path(path)

    def record(
        self, *, actor: str, action: str, target: str, dry_run: bool,
        before: dict | None = None, after: dict | None = None, success: bool = True,
    ) -> AuditEntry:
        entry = AuditEntry(
            timestamp=now_iso(), actor=actor, action=action, target=target,
            dry_run=dry_run, before=before, after=after, success=success,
        )
        with self.path.open("a") as f:
            f.write(json.dumps(entry.__dict__) + "\n")
        return entry

    def read_all(self) -> list[AuditEntry]:
        if not self.path.exists():
            return []
        entries = []
        with self.path.open() as f:
            for line in f:
                if line.strip():
                    entries.append(AuditEntry(**json.loads(line)))
        return entries
