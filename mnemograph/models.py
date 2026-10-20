from datetime import datetime, timezone
from typing import Literal, Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Source(Input):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=20000)
    uri: str = Field(default="", max_length=2000)
    occurred_at: datetime | None = None
    speaker: str = Field(default="agent", max_length=80)
    platform: str = Field(default="manual", max_length=80)
    session_id: str = Field(default="", max_length=100)

    @model_validator(mode="after")
    def aware_source_time(self):
        if self.occurred_at and self.occurred_at.tzinfo is None:
            raise ValueError("Source time must include a timezone")
        return self


class Link(Input):
    target_id: str = Field(min_length=1, max_length=100)
    relation: Literal["SUPPORTS", "SUPERSEDES", "CONTRADICTS", "REFINES", "DUPLICATES", "DERIVED_FROM"]


class Memory(Input):
    title: str = Field(min_length=1, max_length=180)
    kind: Literal["episode", "fact", "decision", "procedure", "core", "resource", "hypothesis", "insight"] = "fact"
    content: str = Field(min_length=1, max_length=20000)
    cues: list[str] = Field(default_factory=list, max_length=20)
    related_ids: list[str] = Field(default_factory=list, max_length=20)
    source: Source
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    status: Literal["asserted", "accepted", "disputed", "superseded", "archived", "rejected"] = "asserted"
    synthetic: bool = False
    dataset: str = Field(default="workspace", pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")
    visibility: Literal["shared", "private"] = "shared"
    shared_with: list[str] = Field(default_factory=list, max_length=30)
    links: list[Link] = Field(default_factory=list, max_length=20)
    source_message_id: str | None = Field(default=None, max_length=100)
    source_trust: Literal["user_stated", "agent_derived", "system_event"] = "agent_derived"
    claim_key: str = Field(default="", max_length=100)
    claim_value: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def valid_interval(self):
        for value in (self.valid_from, self.valid_to):
            if value and value.tzinfo is None:
                raise ValueError("Validity dates must include a timezone")
        if self.valid_to and (not self.valid_from or self.valid_to <= self.valid_from):
            raise ValueError("valid_to must be later than valid_from")
        self.cues = list(dict.fromkeys(cue.casefold() for cue in self.cues if cue.strip()))
        if any(len(cue) > 100 for cue in self.cues):
            raise ValueError("Cues must be at most 100 characters")
        return self


class Write(Input):
    memory: Memory
    idempotency_key: str = Field(min_length=1, max_length=120)
    expected_version: int = Field(default=0, ge=0)


class Recall(Input):
    query: str = Field(min_length=1, max_length=2000)
    budget_chars: int = Field(default=2400, ge=256, le=16000)
    max_hops: int = Field(default=2, ge=0, le=2)
    as_of: datetime | None = None
    dataset: str | None = Field(default=None, max_length=64)
    strategy: Literal["pace", "bm25", "vector", "beam", "ppr", "qwam"] = "pace"
    intent: str | None = Field(default=None, max_length=80)
    cursor: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def aware_time(self):
        if self.as_of and self.as_of.tzinfo is None:
            raise ValueError("as_of must include a timezone")
        return self


class Message(Input):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    role: Literal["user", "assistant", "system", "tool"]
    text: str = Field(min_length=1, max_length=20000)
    at: datetime
    platform: str = Field(default="custom", max_length=80)
    session_id: str = Field(min_length=1, max_length=100)
    dataset: str = Field(default="workspace", pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")
    synthetic: bool = False
    visibility: Literal["shared", "private"] = "shared"
    shared_with: list[str] = Field(default_factory=list, max_length=30)
    idempotency_key: str = Field(min_length=1, max_length=120)

    @model_validator(mode="after")
    def aware_message(self):
        if self.at.tzinfo is None:
            raise ValueError("Message time must include a timezone")
        return self


class Dataset(Input):
    dataset: Literal["personal-assistant", "camera-lab", "team-planning"] = "personal-assistant"


class Forget(Input):
    expected_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=120)


class Checkpoint(Input):
    objective: str = Field(min_length=1, max_length=500)
    completed: list[Annotated[str, Field(max_length=1000)]] = Field(default_factory=list, max_length=20)
    blockers: list[Annotated[str, Field(max_length=1000)]] = Field(default_factory=list, max_length=20)
    next_steps: list[Annotated[str, Field(max_length=1000)]] = Field(default_factory=list, max_length=20)
    memory_ids: list[str] = Field(default_factory=list, max_length=30)
    idempotency_key: str = Field(min_length=1, max_length=120)


class Claim(Input):
    expected_task_version: int = Field(ge=1)
    lease_seconds: int = Field(default=120, ge=30, le=600)
    idempotency_key: str = Field(min_length=1, max_length=120)


class ActionReceipt(Input):
    task_id: str = Field(min_length=1, max_length=100)
    fencing_token: int = Field(ge=1)
    action_id: str = Field(min_length=1, max_length=100)
    external_receipt: str = Field(min_length=1, max_length=4000)
    idempotency_key: str = Field(min_length=1, max_length=120)

class Connect(Input):
    platform: str = Field(min_length=1, max_length=80)
    context: str = Field(default="", max_length=1000)


class Handoff(Input):
    title: str = Field(min_length=1, max_length=180)
    target_agent: str = Field(min_length=1, max_length=80)
    context: str = Field(min_length=1, max_length=4000)
    memory_ids: list[str] = Field(default_factory=list, max_length=30)
    idempotency_key: str = Field(min_length=1, max_length=120)
    expected_version: int = Field(default=0, ge=0)
    status: Literal["open", "in_progress", "completed", "blocked"] = "open"
