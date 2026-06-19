# Agents

An **agent** is an AI participant in a OpenSynod debate. Each agent occupies a named seat at the round table, is backed by a specific LLM, and is configured with a persona, disposition, and set of discussion rules.

## Agent Configuration Schema

```json
{
  "seat_id": "cfo",
  "display_name": "Skeptical CFO",
  "color": "#DC2626",
  "avatar": "calculator",
  "model": "claude-opus-4-7",
  "persona": {
    "role": "Chief Financial Officer",
    "domain_focus": ["financial risk", "ROI", "capital allocation", "balance sheet"],
    "disposition": "skeptic",
    "expertise_level": "expert",
    "system_prompt_overlay": "You are a seasoned CFO with 20 years of experience..."
  },
  "discussion_rules": {
    "must_cite_sources": true,
    "hidden_commitment_required": true,
    "min_challenges_per_session": 2
  }
}
```

**Field reference:**

| Field | Values | Description |
|---|---|---|
| `seat_id` | string | Unique identifier within the panel |
| `display_name` | string | Shown in the UI and transcript |
| `color` | hex color | Used for message bubbles and seat highlighting |
| `avatar` | icon name | Visual identifier in the round-table |
| `model` | LLM identifier | Routes to the appropriate provider client |
| `persona.disposition` | `skeptic`, `advocate`, `neutral`, `devil_advocate`, `expert`, `moderator` | Influences system prompt framing and moderator challenge behavior |
| `persona.expertise_level` | `expert`, `senior`, `mid` | Affects system prompt tone and depth |
| `persona.system_prompt_overlay` | string | Appended to the base system prompt for this seat |
| `discussion_rules.must_cite_sources` | boolean | Agent is prompted to cite sources for factual claims |
| `discussion_rules.hidden_commitment_required` | boolean | Agent participates in the hidden-position commitment protocol |
| `discussion_rules.min_challenges_per_session` | integer | Minimum explicit challenges the agent must make |

