"""Pydantic schemas for panel configuration and validation."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class PersonaConfig(BaseModel):
    role: str
    domain_focus: list[str]
    disposition: Literal["skeptic", "advocate", "neutral", "devil_advocate", "expert", "moderator"]
    expertise_level: Literal["expert", "senior", "mid"]
    system_prompt_overlay: str


class SeatDiscussionRules(BaseModel):
    must_cite_sources: bool = True
    hidden_commitment_required: bool = True
    min_challenges_per_session: int = 0


class SeatConfig(BaseModel):
    seat_id: str
    display_name: str
    color: str
    avatar: str
    model: str
    persona: PersonaConfig
    discussion_rules: SeatDiscussionRules = Field(default_factory=SeatDiscussionRules)

    @property
    def provider(self) -> str:
        m = self.model.lower()
        if m.startswith("claude"):
            return "anthropic"
        if m.startswith(("gpt-", "o3", "o1")):
            return "openai"
        if m.startswith("gemini"):
            return "google"
        return "ollama"


class ModeratorConfig(BaseModel):
    model: str = "claude-opus-4-7"
    system_prompt: str = ""
    auto_summary_every_n_turns: int = 10
    convergence_speed_threshold: int = 3


class PanelDiscussionRules(BaseModel):
    hidden_position_protocol: bool = True
    min_turns_before_convergence: int = 8
    max_turns: int = 50
    allowed_tools: list[str] = Field(default_factory=lambda: ["web_search", "document_search"])
    adversarial_framing: bool = False


class PanelSchema(BaseModel):
    id: str
    name: str
    description: str
    use_cases: list[str]
    seats: list[SeatConfig]
    moderator_config: ModeratorConfig
    discussion_rules: PanelDiscussionRules
    is_system: bool = True


    def has_devil_advocate(self) -> bool:
        return any(s.persona.disposition == "devil_advocate" for s in self.seats)

    def get_devil_advocate(self) -> SeatConfig | None:
        for seat in self.seats:
            if seat.persona.disposition == "devil_advocate":
                return seat
        return None

    def to_db_dict(self) -> dict[str, Any]:
        return {
            "seats_json": [s.model_dump() for s in self.seats],
            "moderator_config_json": self.moderator_config.model_dump(),
            "discussion_rules_json": self.discussion_rules.model_dump(),
        }


class PanelResponse(BaseModel):
    id: str
    name: str
    description: str
    use_cases: list[str]
    seats: list[SeatConfig]
    moderator_config: ModeratorConfig
    discussion_rules: PanelDiscussionRules
    is_system: bool

    model_config = {"from_attributes": True}
