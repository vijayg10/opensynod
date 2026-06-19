# Key Features

## Curated Expert Panels

OpenSynod ships with few pre-built panels, each optimized for a specific decision type. Panels define everything needed for a session: which agent seats exist, which LLM backs each seat, what persona and domain focus each agent has, and which discussion rules apply.

**Available panels:**

| Panel | Use Case |
|---|---|
| M&A Due Diligence | Acquisition analysis, deal assessment, term sheet review |
| Go-to-Market Strategy | Market entry, launch planning, channel decisions |
| Risk & Compliance | Regulatory review, risk assessment, compliance analysis |
| Technical Architecture | System design, build vs. buy, platform decisions |
| Pricing Decision | Pricing strategy, packaging, tier design |

**One-click start.** Selecting a panel and clicking Start is all that is required. No agent configuration needed.

**Customizable.** Customization can be done using the configuration file by referring to the existing panels and structure.

---

## Live Source Citation

Every agent in a session can search the web in real time. Sources retrieved during the discussion are collected in a **Sources** tab in the side panel, showing the title, URL, and domain of each reference.

**What this means in practice:**
- Arguments are anchored to current information, not stale training data
- The outcome document includes a full source bibliography

---

## Multi-Human Collaboration

Multiple team members can join the same session simultaneously. Each participant sees the live discussion and can intervene at any time.

**Human capabilities during a session:**
- Inject a question or redirect the discussion via a free-text intervention
- Cast a formal vote on the final recommendation

**Asynchronous participation.** The full voting UI is accessible without attending the live session.

---

## Human Voting on Recommendations

The Moderator's proposed recommendation is not final. It enters a formal voting phase.

**The voting sequence:**

1. Moderator presents the proposed recommendation with supporting arguments and curated dissent
2. Each agent casts a structured vote (Yes / No / Abstain) with a one-sentence rationale
3. Humans see the full agent vote distribution before voting
4. Humans cast their votes with an optional rationale field
5. The final record shows agent votes and human votes separately

**Possible outcomes:**
- Recommendation — agents reached consensus and the vote passed
- No consensus — documented with each position's reasoning preserved

---

## Full Auditability

Every action in a OpenSynod session is logged with actor, timestamp, and content. The audit record is append-only — no message or event can be retroactively deleted.

**What the audit record contains:**
- Full message transcript with timestamps (including human interventions)
- Agent configurations and panel definition used
- All source citations (URL, title, domain)
- All votes with rationale
- Session metadata: topic, outcome type, cost

**Exportable.** The complete record exports as PDF, Markdown, or structured JSON. The JSON export is HMAC-signed for tamper evidence.

---

## Anti-Sycophancy Design

One of the biggest risks in multi-agent AI is that models agree with each other too easily. OpenSynod builds several mechanisms to counter this:

**Hidden-position commitment:** Before any agent sees what others think, each agent privately commits an initial position. Opening statements are generated from those committed positions. This prevents the first speaker from anchoring everyone else.

**Forced devil's advocate:** Every panel includes at least one agent explicitly configured as a skeptic or devil's advocate. This seat is required to challenge the emerging consensus.

**Moderator challenge injection:** If the Moderator detects that agents are converging suspiciously fast — without enough genuine challenge — it injects a challenge prompt to the skeptic before allowing the discussion to advance.

**Cross-model diversity:** Curated panels require at least two distinct LLM providers. Different model families have genuinely different biases and tendencies.


---

## Honest Outcomes

OpenSynod is designed to surface truth, not manufacture agreement.

**"No consensus" is a first-class output.** When agents genuinely disagree, the product says so explicitly — with minority positions preserved in the substantive dissents.

**Confidence indicator.** The outcome document shows a confidence score derived from the vote spread. A strong consensus is reported as such; a narrow one is reported as such.

**Source density indicator.** The outcome document shows the proportion of agent messages that cited sources during the discussion.

**Substantive dissent is preserved.** The Moderator curates which minority positions have real argumentative weight and surfaces them on the outcome screen. Minority views do not disappear because they lost the vote.

---

## Cost Transparency

Multi-model discussions with web search consume real tokens and cost real money. OpenSynod makes this visible.

- Pre-session cost estimate on the Topic Setup screen
- Live cost counter in the session header, updated in real time
- Configurable cost cap: the session concludes when the limit is reached
- Per-session cost included in the audit record

---

## Real-Time Streaming

Agent messages stream token-by-token as they are generated. There is no waiting for a complete response — you see agents thinking in real time.

- All participants see the same live stream of the discussion
- Phase changes, new sources, and votes appear instantly
- If your connection drops, it reconnects automatically without losing any messages
