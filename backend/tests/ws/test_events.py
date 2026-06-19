"""Tests for WebSocket/SSE event types (Phase 6)."""

from __future__ import annotations

import json

from app.ws.events import SSEEvent


class TestSSEEvent:
    def test_to_sse_bytes_format(self) -> None:
        event = SSEEvent(event="token", data={"seat_id": "cfo", "token": "hello"})
        raw = event.to_sse_bytes()
        text = raw.decode()

        assert text.startswith("event: token\n")
        assert "data: " in text
        assert text.endswith("\n\n")

    def test_data_is_valid_json(self) -> None:
        event = SSEEvent(event="phase_change", data={"from": "opening", "to": "exploration"})
        raw = event.to_sse_bytes()
        text = raw.decode()

        # Extract data line
        for line in text.split("\n"):
            if line.startswith("data: "):
                payload = json.loads(line.removeprefix("data: "))
                assert payload["from"] == "opening"
                assert payload["to"] == "exploration"
                break

    def test_all_sse_event_types_valid(self) -> None:
        event_types = [
            "token", "message_start", "message_end", "source_start", "source_ready",
            "phase_change", "intervention", "summary_ready", "vote_update",
            "session_state", "cost_update", "cost_cap_hit", "agent_themes",
            "presence_update", "error",
        ]
        for event_type in event_types:
            event = SSEEvent(event=event_type, data={})  # type: ignore[arg-type]
            raw = event.to_sse_bytes()
            assert f"event: {event_type}" in raw.decode()
