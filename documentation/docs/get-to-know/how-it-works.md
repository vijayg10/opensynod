# How It Works

A OpenSynod session takes your team from a strategic question to a clear, documented recommendation in a structured, seven-screen flow. Here is what that looks like from start to finish.

## The Flow at a Glance

![The Flow at a Glance](/opensynod-flow-at-glance.drawio.svg)


## Step 1: Sign-In to the Dashboard

The entry point. You see your team's discussion history — past sessions with their outcomes, in-progress sessions others have started, and saved templates.

Click **Start New Discussion** to begin.


## Step 2: Topic Setup

Define what is being decided.

- **Decision question** — the specific question being put to the panel (required)
- **Desired outcome type** — are you looking for a recommendation, an exploration, or a risk assessment?
- **Success criteria** — what would a good outcome look like? (optional)

Once you select a panel in the next step, a sidebar shows the estimated cost, number of turns, and expected duration.


## Step 3: Panel Selection

Choose the expert panel for your decision type. Examples: Go-to-Market Strategy, M&A Due Diligence, Technical Architecture, Pricing Decision...etc

Panels are pre-built configurations optimized for specific decision categories. Each one defines:
- Which agents sit at the table (3–7 seats)
- Which LLM backs each agent
- What persona and domain focus each agent has
- Which discussion rules apply:
  - **Devil's advocate requirement** — at least one agent seat is explicitly configured as a skeptic, required to challenge the emerging consensus
  - **Hidden-position commitment** — each agent privately commits an initial position before seeing what others think, preventing the first speaker from anchoring the group
  - **Source citation requirement** — agents must cite sources when making factual claims during the debate phase


## Step 4: Discussion Rules

Set session parameters. All fields have sensible defaults.

| Setting | Default | What it controls |
|---|---|---|
| Speaking order | Round Robin | Order in which agents speak — Round Robin, Dynamic, or Moderator Assigned |
| Allow human interventions | On | Whether you can send messages during the discussion |
| Require citations | Off | Agents must cite sources for factual claims |
| Anonymize agents | Off | Hide agent names and models during the discussion |
| Max turns per phase | 4 | How many turns each phase runs |
| Opening statement words | 200 | Word limit for opening statements |
| Rebuttal words | 150 | Word limit for rebuttal messages |

Click **Start Discussion** to launch.


## Step 5: The Live Discussion

This is the core experience. The screen has three zones:

### Round-Table Visualization

Agent seats arranged in a circle. The active speaker is highlighted with an animated pulse ring while thinking and generating a response. Each seat shows the agent's persona name.

Human participants are shown separately around the table.

### Live Transcript

Messages stream token-by-token as agents think. Each message shows the agent's persona name, model, phase, timestamp, and message text.

Sources cited during the discussion are collected in a **Sources** tab in the side panel, showing the title, URL, and domain of each reference.

### Control Bar

A persistent input bar lets you **intervene at any time** — type a message to inject a question, request a clarification, or redirect the discussion.

Additional controls let you **pause**, **skip a turn**, or **end the discussion**.

The discussion moves through five phases, managed by a Moderator agent:

1. **Opening positions** — each agent states their initial view
2. **Exploration** — agents question and build on each other's positions
3. **Debate** — explicit challenges, source citations introduced
4. **Convergence** — the Moderator synthesizes areas of agreement and disagreement
5. **Vote** — the Moderator presents its recommended conclusion

---

## Step 6: Voting Phase

When the Moderator concludes the discussion, the screen transitions to voting.

You see:
- The **proposed recommendation** (or "no consensus" statement)
- **Key supporting arguments**
- **Substantive dissents** — minority positions that have real weight, with their reasoning preserved
- **Agent votes** — each agent's Yes/No/Abstain with a one-sentence rationale

Agents vote first. You see the agent distribution before casting your own vote. Human votes include an optional rationale field.

When voting closes, the final tally is recorded: agent votes and human votes separately. If humans override the agent recommendation, that divergence is explicitly noted.

---

## Step 7: Outcome & Audit Record

The final document. Every session concludes with a structured record that includes:

- The recommendation (or "no consensus" with documented reasons)
- Vote breakdown — agents and humans separately
- Key supporting arguments
- Substantive dissent — preserved minority positions
- Confidence indicator — how strongly was consensus reached?
- Source density indicator — how grounded in cited sources was the discussion?
- Full source bibliography
- Complete transcript (filterable by agent or phase)
- Agent configurations
- Participating humans and their votes
- Export options: PDF, Markdown, JSON

Teams can also **mark the decision outcome later** — did we adopt this recommendation? Did it work?
