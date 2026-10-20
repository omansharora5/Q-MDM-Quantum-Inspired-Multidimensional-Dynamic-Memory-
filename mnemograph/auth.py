import hashlib
import json
import secrets
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Scope:
    tenant: str
    project: str
    agent: str
    actions: frozenset[str]

    @property
    def namespace(self):
        return hashlib.sha256(f"{self.tenant}\0{self.project}".encode()).hexdigest()[:32]


class DomainError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message


class Credentials:
    def __init__(self, entries: list[dict]):
        self.entries = entries

    def authorize(self, token: str, action: str = "read") -> Scope:
        digest = hashlib.sha256(token.encode()).hexdigest()
        entry = next((item for item in self.entries if secrets.compare_digest(item["digest"], digest)), None)
        if not entry:
            raise DomainError(401, "A valid scoped API key is required")
        if action not in entry["actions"]:
            raise DomainError(403, f"Credential does not permit {action}")
        return Scope(entry["tenant"], entry["project"], entry["agent"], frozenset(entry["actions"]))

    def agents(self, scope: Scope) -> list[str]:
        return sorted({entry["agent"] for entry in self.entries
                       if entry["tenant"] == scope.tenant and entry["project"] == scope.project})


def initialize(directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    auth_path = directory / "credentials.json"
    if auth_path.exists():
        return
    entries, keys = [], {}
    for agent in ("operator", "researcher", "developer"):
        token = secrets.token_urlsafe(32)
        keys[agent] = token
        entries.append({"digest": hashlib.sha256(token.encode()).hexdigest(), "tenant": "local",
                        "project": "mnemograph", "agent": agent,
                        "actions": ["read", "write", "coordinate"]})
    (directory / "keys.json").write_text(json.dumps(keys, indent=2), encoding="utf-8")
    auth_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")
