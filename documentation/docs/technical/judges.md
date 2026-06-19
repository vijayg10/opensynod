# Judges / Moderators

The **Moderator** is a special agent present in every OpenSynod session. Unlike other agents, it never advocates for positions, expresses opinions, or debates. Its role is purely facilitative.

## Responsibilities

- Advance the discussion through five phases: Opening → Exploration → Debate → Convergence → Vote
- Select the next speaker strategically to maximize insight and diversity
- Detect sycophancy: if agents converge without sufficient challenge, direct the devil's advocate before advancing
- Generate auto-summaries every N turns
- Curate substantive dissent for the outcome document
- Produce the final recommendation or "no consensus" statement
- Collect each agent's structured vote in the voting phase

---

## Structured Output

The Moderator communicates flow decisions through a structured tool call (`make_moderator_decision`). This ensures machine-readable, validated output for:

- `next_speaker` — which agent speaks next
- `phase_transition` — when to advance to the next phase
- `inject_challenge` — force the next speaker to challenge the emerging consensus
- `challenge_target` — the seat whose position should be challenged
- `summary` — auto-summary of the current discussion state

The final outcome is produced through a separate `make_recommendation` tool (the recommendation or "no consensus" statement), and votes through a `cast_vote` tool. The Moderator never outputs free-form decisions that require string parsing.

**Model:** The Moderator is backed by the most capable configured model (default: `claude-opus-4-7`).

---

## Anti-Sycophancy Mechanisms

The biggest risk in multi-agent AI is groupthink. The Moderator is the primary enforcement point for four countermeasures:

### 1. Hidden-Position Commitment

For panels with `hidden_position_protocol: true`:

1. **Commit phase:** Before opening statements, each agent privately commits their initial position in one sentence. Responses are stored with `hidden: true` and not broadcast to other agents.
2. **Reveal phase:** Opening statement prompts include the agent's own commitment as context. Other agents' commitments remain hidden until all opening statements are delivered.
3. **Persistence:** Hidden commitments are kept in the append-only message record (flagged `hidden_commitment`), but remain excluded from the transcript, the public API, and exports.

### 2. Forced Devil's Advocate

Curated panels include a seat with `disposition: "devil_advocate"`. This agent is explicitly instructed to challenge the emerging consensus, even when its own analysis might agree. The goal is to surface the best available counterarguments — not to represent a genuinely skeptical viewpoint. The Moderator detects the devil's advocate seat via the panel configuration (`get_devil_advocate`).

### 3. Moderator Challenge Injection

If the Moderator detects that agents are converging faster than expected — fewer than a threshold number of explicit challenges before the Convergence phase — it injects a challenge prompt directed at the devil's advocate seat. This forces one more round of substantive challenge before synthesis.

### 4. Cross-Model Diversity

Panels can mix models from different LLM providers so that no single model's biases dominate the discussion. Each seat's `model` is routed to its provider independently.

---

## "No Consensus" as a First-Class Output

When agents genuinely disagree, the Moderator produces a "no consensus" statement explicitly — with each position documented, including what would need to be true for each to win. This is not a failure state — it is the honest result.

The outcome document shows:

- **Confidence indicator** — derived from the agent vote tally (the share of "yes" votes). A strong consensus is reported as such; a narrow one is flagged.
- **Substantive dissent** — minority positions with real argumentative weight are curated and preserved, even if they lost the vote.
- **Source density indicator** — what percentage of claims were backed by cited sources. Low-citation discussions are flagged as less grounded.

