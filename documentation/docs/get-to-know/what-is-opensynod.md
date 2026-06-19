# What is OpenSynod?

OpenSynod is an open-source multi-agent AI discussion platform where panels of AI personas — each backed by a different language model — deliberate on a question, debate perspectives, and produce a structured, auditable recommendation.

Instead of asking a single AI for an answer, you convene a quorum: a curated panel of agents with distinct roles, models, and viewpoints. They challenge each other, cite sources, and vote. You get a recommendation backed by documented reasoning, not a single model's best guess.

**About the name:** *synod* comes from the Greek *syn* ("together") and *hodos* ("road") — literally "a coming together" or "a meeting along the way." It has come to mean a deliberative assembly convened to debate an issue and reach a collective decision — exactly what a panel of agents does here.

---

## The Problem It Solves

Single-model AI responses are fast but brittle. One model has one perspective, one set of biases, and no one to push back on it. In high-stakes decisions — acquisitions, architecture choices, risk assessments, pricing — that's not good enough.

OpenSynod builds in adversarial structure by design:

- **Cross-model diversity** — curated panels require at least two distinct LLM providers. Different model families have genuinely different tendencies and biases.
- **Hidden-position commitment** — each agent privately commits an initial position before seeing what others think. This prevents the first speaker from anchoring everyone else.
- **Forced devil's advocate** — every panel includes a skeptic seat, required to challenge the emerging consensus.
- **Moderator challenge injection** — if agents converge suspiciously fast, the Moderator injects a challenge before allowing the discussion to advance.

---

## Who It's For

- **Strategy and product teams** making high-stakes decisions that benefit from structured deliberation
- **Engineering teams** evaluating architecture choices, build vs. buy, or platform decisions
- **Anyone** who wants more than one AI perspective on an important question

---

## Key Concepts

| Concept | Description |
|---|---|
| **Agent** | An AI participant backed by a specific LLM, with a persona and role |
| **Panel** | A curated group of agents optimized for a specific decision category |
| **Quorum (Session)** | A structured debate from topic setup to outcome document |
| **Moderator** | A special agent that manages phases and synthesizes consensus |
| **Outcome** | A structured recommendation with votes, dissents, and a full audit trail |

---

## Open Source

OpenSynod is Apache 2.0 licensed and designed for on-premises deployment. No data leaves your infrastructure. LLM calls go directly from your cluster to provider APIs.

[View on GitHub →](https://github.com/vijayg10/opensynod)
