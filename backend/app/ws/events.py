"""SSE and WebSocket event type definitions."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

# ------------------------------------------------------------------ #
# Server → Client SSE events (published via Redis pub/sub)
# ------------------------------------------------------------------ #

SSEEventType = Literal[
    "token",
    "message_start",
    "message_end",
    "source_start",
    "source_ready",
    "phase_change",
    "intervention",
    "summary_ready",
    "vote_update",
    "session_state",
    "cost_update",
    "cost_cap_hit",
    "agent_themes",
    "presence_update",
    "error",
]


class SSEEvent(BaseModel):
    event: SSEEventType
    data: dict[str, Any]

    def to_sse_bytes(self) -> bytes:
        """Format as SSE text (event: ...\ndata: ...\n\n)."""
        import json
        payload = json.dumps(self.data, default=str)
        return f"event: {self.event}\ndata: {payload}\n\n".encode()


# ------------------------------------------------------------------ #
# Client → Server WebSocket message types
# ------------------------------------------------------------------ #

class WSAuthMessage(BaseModel):
    type: Literal["auth"]
    token: str


class WSInterventionMessage(BaseModel):
    type: Literal["intervention"]
    target: str  # "all" or a seat_id
    content: str


class WSPresencePingMessage(BaseModel):
    type: Literal["presence_ping"]
    user_id: str


class WSFlagSourceMessage(BaseModel):
    type: Literal["flag_source"]
    source_id: str
    notes: str = ""


class WSReactionMessage(BaseModel):
    type: Literal["reaction"]
    message_id: str
    reaction: str


class WSVoteMessage(BaseModel):
    type: Literal["vote"]
    vote: Literal["yes", "no", "abstain"]
    rationale: str = ""


# ------------------------------------------------------------------ #
# Server → Client WebSocket messages
# ------------------------------------------------------------------ #

class WSAuthOKMessage(BaseModel):
    type: Literal["auth_ok"] = "auth_ok"
    user_id: str
    display_name: str


class WSPresenceUpdateMessage(BaseModel):
    type: Literal["presence_update"] = "presence_update"
    users: list[dict[str, Any]]


class WSErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    code: str
    message: str
