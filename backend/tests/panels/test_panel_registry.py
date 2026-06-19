"""Tests for Panel Registry (Phase 4)."""

from __future__ import annotations

import pytest

from app.panels.schemas import (
    ModeratorConfig,
    PanelDiscussionRules,
    PanelSchema,
    PersonaConfig,
    SeatConfig,
    SeatDiscussionRules,
)
from app.panels.seed_data import SYSTEM_PANELS
from app.panels.registry import PanelRegistry


def _make_seat(seat_id: str, model: str, disposition: str = "neutral") -> SeatConfig:
    return SeatConfig(
        seat_id=seat_id,
        display_name=seat_id,
        color="#000000",
        avatar="icon",
        model=model,
        persona=PersonaConfig(
            role=seat_id,
            domain_focus=[],
            disposition=disposition,  # type: ignore[arg-type]
            expertise_level="expert",
            system_prompt_overlay="",
        ),
        discussion_rules=SeatDiscussionRules(),
    )


def _make_panel(seats: list[SeatConfig]) -> PanelSchema:
    return PanelSchema(
        id="test-id",
        name="Test Panel",
        description="A test panel",
        use_cases=[],
        seats=seats,
        moderator_config=ModeratorConfig(),
        discussion_rules=PanelDiscussionRules(),
    )


class TestModelDiversityValidation:
    def test_accepts_panel_with_multiple_providers(self) -> None:
        seats = [
            _make_seat("a", "claude-opus-4-7"),
            _make_seat("b", "gpt-4o"),
        ]
        panel = _make_panel(seats)
        assert panel is not None

    def test_rejects_panel_with_single_provider(self) -> None:
        seats = [
            _make_seat("a", "claude-opus-4-7"),
            _make_seat("b", "claude-sonnet-4-6"),
        ]
        with pytest.raises(ValueError, match="at least 2 distinct"):
            _make_panel(seats)

    def test_validates_diversity(self) -> None:
        seats_single = [
            _make_seat("a", "claude-opus-4-7"),
            _make_seat("b", "claude-sonnet-4-6"),
        ]
        assert not PanelRegistry.validate_diversity(seats_single)

        seats_multi = [
            _make_seat("a", "claude-opus-4-7"),
            _make_seat("b", "gpt-4o"),
        ]
        assert PanelRegistry.validate_diversity(seats_multi)


class TestProviderDetection:
    def test_anthropic_models(self) -> None:
        assert _make_seat("x", "claude-opus-4-7").provider == "anthropic"
        assert _make_seat("x", "claude-sonnet-4-6").provider == "anthropic"

    def test_openai_models(self) -> None:
        assert _make_seat("x", "gpt-4o").provider == "openai"
        assert _make_seat("x", "gpt-4o-mini").provider == "openai"
        assert _make_seat("x", "o3").provider == "openai"

    def test_google_models(self) -> None:
        assert _make_seat("x", "gemini-2.5-pro").provider == "google"

    def test_ollama_models(self) -> None:
        assert _make_seat("x", "llama3").provider == "ollama"
        assert _make_seat("x", "mistral").provider == "ollama"


class TestSeedData:
    def test_all_5_panels_present(self) -> None:
        assert len(SYSTEM_PANELS) == 5

    def test_all_panels_have_valid_ids(self) -> None:
        ids = [p["id"] for p in SYSTEM_PANELS]
        assert len(set(ids)) == 5  # no duplicates

    @pytest.mark.parametrize("panel_dict", SYSTEM_PANELS)
    def test_panel_validates_correctly(self, panel_dict: dict) -> None:
        seats = [SeatConfig.model_validate(s) for s in panel_dict["seats"]]
        schema = PanelSchema(
            id=panel_dict["id"],
            name=panel_dict["name"],
            description=panel_dict["description"],
            use_cases=panel_dict["use_cases"],
            seats=seats,
            moderator_config=ModeratorConfig.model_validate(panel_dict["moderator_config"]),
            discussion_rules=PanelDiscussionRules.model_validate(panel_dict["discussion_rules"]),
        )
        assert schema.name == panel_dict["name"]

    @pytest.mark.parametrize("panel_dict", SYSTEM_PANELS)
    def test_panel_has_model_diversity(self, panel_dict: dict) -> None:
        seats = [SeatConfig.model_validate(s) for s in panel_dict["seats"]]
        assert PanelRegistry.validate_diversity(seats), (
            f"Panel '{panel_dict['name']}' does not have sufficient model diversity"
        )

    @pytest.mark.parametrize("panel_dict", SYSTEM_PANELS)
    def test_panel_has_devil_advocate(self, panel_dict: dict) -> None:
        seats = [SeatConfig.model_validate(s) for s in panel_dict["seats"]]
        schema = PanelSchema(
            id=panel_dict["id"],
            name=panel_dict["name"],
            description=panel_dict["description"],
            use_cases=panel_dict["use_cases"],
            seats=seats,
            moderator_config=ModeratorConfig.model_validate(panel_dict["moderator_config"]),
            discussion_rules=PanelDiscussionRules.model_validate(panel_dict["discussion_rules"]),
        )
        assert schema.has_devil_advocate(), (
            f"Panel '{panel_dict['name']}' has no devil_advocate seat"
        )

    @pytest.mark.parametrize("panel_dict", SYSTEM_PANELS)
    def test_panel_snapshot_roundtrip(self, panel_dict: dict) -> None:
        seats = [SeatConfig.model_validate(s) for s in panel_dict["seats"]]
        schema = PanelSchema(
            id=panel_dict["id"],
            name=panel_dict["name"],
            description=panel_dict["description"],
            use_cases=panel_dict["use_cases"],
            seats=seats,
            moderator_config=ModeratorConfig.model_validate(panel_dict["moderator_config"]),
            discussion_rules=PanelDiscussionRules.model_validate(panel_dict["discussion_rules"]),
        )
        snapshot = PanelRegistry.build_snapshot(schema)
        restored = PanelSchema.model_validate(snapshot)
        assert restored.id == schema.id
        assert restored.name == schema.name
        assert len(restored.seats) == len(schema.seats)
