import { useState, useMemo } from "react";
import { useParams, useNavigate } from "@tanstack/react-router";
import AppNavbar from "@/components/AppNavbar";
import {
  useSession,
  useSessionOutcome,
  useSessionMessages,
  useSessionSources,
  useSessionVotes,
  useSessionAudit,
  useMarkDecisionOutcome,
  useExportSession,
} from "@/hooks/useSessions";
import type { Vote, ApiMessage } from "@/types/api";

// ─── SVG Donut Chart ───────────────────────────────────────────────────────

interface DonutSlice {
  value: number;
  color: string;
  label: string;
}

function DonutChart({ slices, size = 120 }: { slices: DonutSlice[]; size?: number }) {
  const total = slices.reduce((s, d) => s + d.value, 0) || 1;
  const cx = size / 2;
  const cy = size / 2;
  const r = size * 0.36;
  const stroke = size * 0.15;

  let offset = 0;
  const circumference = 2 * Math.PI * r;

  return (
    <svg width={size} height={size} role="img" aria-label="Vote distribution donut chart">
      {slices.map((slice, i) => {
        const pct = slice.value / total;
        const dashLen = pct * circumference;
        const dashGap = circumference - dashLen;
        const rotation = offset * 360 - 90;
        offset += pct;
        return (
          <circle
            key={i}
            cx={cx}
            cy={cy}
            r={r}
            fill="none"
            stroke={slice.color}
            strokeWidth={stroke}
            strokeDasharray={`${dashLen} ${dashGap}`}
            strokeDashoffset={0}
            transform={`rotate(${rotation} ${cx} ${cy})`}
          />
        );
      })}
      <text x={cx} y={cy + 1} textAnchor="middle" dominantBaseline="middle" fill="#111827" fontSize={size * 0.14} fontWeight="600">
        {total}
      </text>
      <text x={cx} y={cy + size * 0.13} textAnchor="middle" dominantBaseline="middle" fill="#6b7280" fontSize={size * 0.1}>
        votes
      </text>
    </svg>
  );
}

// ─── Confidence Gauge ──────────────────────────────────────────────────────

function ConfidenceGauge({ score }: { score: number }) {
  const pct = Math.max(0, Math.min(1, score));
  const color = pct > 0.7 ? "#10b981" : pct > 0.4 ? "#f59e0b" : "#ef4444";
  const r = 38;
  const circumference = Math.PI * r; // half circle
  const dash = pct * circumference;

  return (
    <div className="flex flex-col items-center">
      <svg width="90" height="52" role="img" aria-label={`Confidence score: ${Math.round(pct * 100)}%`}>
        <path
          d={`M 8 46 A ${r} ${r} 0 0 1 82 46`}
          fill="none"
          stroke="#e5e7eb"
          strokeWidth="10"
          strokeLinecap="round"
        />
        <path
          d={`M 8 46 A ${r} ${r} 0 0 1 82 46`}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circumference}`}
        />
        <text x="45" y="44" textAnchor="middle" fill="#111827" fontSize="14" fontWeight="700">
          {Math.round(pct * 100)}
        </text>
      </svg>
      <span className="text-xs text-gray-500 mt-1">Confidence</span>
    </div>
  );
}

// ─── Source Density Indicator ──────────────────────────────────────────────

function SourceDensityIndicator({ score }: { score: number }) {
  const pct = Math.max(0, Math.min(1, score));
  const color = pct > 0.6 ? "text-emerald-600" : pct > 0.3 ? "text-amber-600" : "text-gray-500";

  return (
    <div className="flex flex-col items-center">
      <div className="w-[90px] h-[52px] flex items-center justify-center">
        <span className={`text-2xl font-bold ${color}`}>
          {Math.round(pct * 100)}%
        </span>
      </div>
      <span className="text-xs text-gray-500">Source Coverage</span>
    </div>
  );
}

// ─── Transcript Viewer ─────────────────────────────────────────────────────

function renderMessageContent(content: string) {
  if (content.includes("<think>")) {
    const parts = content.split("<think>");
    const afterThink = parts[1] || "";
    if (afterThink.includes("</think>")) {
      const subParts = afterThink.split("</think>");
      const thinkingContent = subParts[0].trim();
      const cleanContent = (parts[0] + subParts[1]).trim();
      return (
        <div className="space-y-2 mt-1">
          <details className="group border-l-2 border-gray-200 pl-3">
            <summary className="cursor-pointer text-xs text-gray-400 hover:text-gray-600 transition list-none flex items-center gap-1 focus:outline-none">
              <svg className="w-3 h-3 transition-transform group-open:rotate-90" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
              Thought Process
            </summary>
            <div className="mt-1.5 text-xs text-gray-500 font-mono bg-gray-50 rounded-lg p-2 max-h-40 overflow-y-auto whitespace-pre-wrap leading-relaxed">
              {thinkingContent}
            </div>
          </details>
          <div className="whitespace-pre-wrap">{cleanContent}</div>
        </div>
      );
    }
  }
  return <div className="whitespace-pre-wrap">{content}</div>;
}

function TranscriptViewer({
  messages,
  seats,
}: {
  messages: ApiMessage[];
  seats: Array<{ seat_id: string; display_name: string; color: string }>;
}) {
  const [filterSeat, setFilterSeat] = useState<string>("all");
  const [filterPhase, setFilterPhase] = useState<string>("all");

  const phases = useMemo(() => {
    const p = new Set(messages.map((m) => m.phase_at_creation).filter(Boolean));
    return Array.from(p) as string[];
  }, [messages]);

  const filtered = useMemo(() => {
    return messages.filter((m) => {
      if (filterSeat !== "all" && m.seat_id !== filterSeat) return false;
      if (filterPhase !== "all" && m.phase_at_creation !== filterPhase) return false;
      return true;
    });
  }, [messages, filterSeat, filterPhase]);

  function getSeatColor(seatId: string | null) {
    if (!seatId) return "#6b7280";
    return seats.find((s) => s.seat_id === seatId)?.color ?? "#6b7280";
  }

  function getSeatName(seatId: string | null) {
    if (!seatId) return "System";
    return seats.find((s) => s.seat_id === seatId)?.display_name ?? seatId;
  }

  return (
    <div>
      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <select
          value={filterSeat}
          onChange={(e) => setFilterSeat(e.target.value)}
          className="bg-white border border-gray-200 rounded-lg px-3 py-1.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          aria-label="Filter by agent"
        >
          <option value="all">All agents</option>
          {seats.map((s) => (
            <option key={s.seat_id} value={s.seat_id}>
              {s.display_name}
            </option>
          ))}
        </select>
        <select
          value={filterPhase}
          onChange={(e) => setFilterPhase(e.target.value)}
          className="bg-white border border-gray-200 rounded-lg px-3 py-1.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          aria-label="Filter by phase"
        >
          <option value="all">All phases</option>
          {phases.map((p) => (
            <option key={p} value={p}>
              {p.charAt(0).toUpperCase() + p.slice(1)}
            </option>
          ))}
        </select>
        <span className="text-xs text-gray-500 self-center">
          {filtered.length} / {messages.length} messages
        </span>
      </div>

      {/* Message list */}
      <div className="space-y-3 max-h-96 overflow-y-auto pr-2 custom-scrollbar">
        {filtered.map((msg) => (
          <article
            key={msg.id}
            className="flex gap-3"
            aria-label={`Message from ${getSeatName(msg.seat_id)}`}
          >
            <div
              className="w-7 h-7 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold mt-0.5"
              style={{
                backgroundColor: getSeatColor(msg.seat_id) + "33",
                color: getSeatColor(msg.seat_id),
              }}
              aria-hidden
            >
              {getSeatName(msg.seat_id).charAt(0)}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-baseline gap-2 mb-0.5">
                <span className="text-xs font-semibold text-gray-900">
                  {getSeatName(msg.seat_id)}
                </span>
                {msg.phase_at_creation && (
                  <span className="text-xs text-gray-400">{msg.phase_at_creation}</span>
                )}
              </div>
              <div className="text-sm text-gray-600 leading-relaxed break-words mt-1">
                {renderMessageContent(msg.content)}
              </div>
            </div>
          </article>
        ))}
        {filtered.length === 0 && (
          <p className="text-sm text-gray-500 text-center py-8">No messages match the filter.</p>
        )}
      </div>
    </div>
  );
}

// ─── Decision Outcome Tracking ─────────────────────────────────────────────

function DecisionOutcomeTracker({ sessionId }: { sessionId: string }) {
  const [result, setResult] = useState<"adopted_success" | "adopted_failure" | "chose_differently" | null>(null);
  const [notes, setNotes] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const markMutation = useMarkDecisionOutcome(sessionId);

  const OPTIONS: Array<{
    value: "adopted_success" | "adopted_failure" | "chose_differently";
    label: string;
    description: string;
    color: string;
  }> = [
    {
      value: "adopted_success",
      label: "Adopted — Worked",
      description: "We implemented the recommendation and it succeeded.",
      color: "border-emerald-300 bg-emerald-50 text-emerald-700",
    },
    {
      value: "adopted_failure",
      label: "Adopted — Failed",
      description: "We implemented the recommendation but it didn't work as hoped.",
      color: "border-red-300 bg-red-50 text-red-700",
    },
    {
      value: "chose_differently",
      label: "Chose Differently",
      description: "We went with a different approach.",
      color: "border-gray-300 bg-gray-50 text-gray-600",
    },
  ];

  async function handleSubmit() {
    if (!result) return;
    await markMutation.mutateAsync({ result, notes: notes || undefined });
    setSubmitted(true);
  }

  if (submitted) {
    return (
      <div className="flex items-center gap-2 text-sm text-emerald-600">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
        Decision outcome recorded. Thank you.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-500">
        Once you've acted on this recommendation, come back and mark the outcome.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => setResult(opt.value)}
            className={`p-4 rounded-xl border text-left transition focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
              result === opt.value
                ? opt.color
                : "border-gray-200 text-gray-500 hover:border-gray-300 hover:text-gray-700"
            }`}
            aria-pressed={result === opt.value}
          >
            <p className="text-sm font-medium mb-1">{opt.label}</p>
            <p className="text-xs opacity-70">{opt.description}</p>
          </button>
        ))}
      </div>

      {result && (
        <>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Additional notes (optional)…"
            rows={2}
            className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-900 placeholder-gray-400 resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <button
            onClick={() => void handleSubmit()}
            disabled={markMutation.isPending}
            className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium rounded-xl transition"
          >
            {markMutation.isPending ? "Saving…" : "Record Outcome"}
          </button>
        </>
      )}
    </div>
  );
}

// ─── Export Bar ────────────────────────────────────────────────────────────

function ExportBar({ sessionId }: { sessionId: string }) {
  const exporter = useExportSession(sessionId);
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleExport(format: "json" | "markdown" | "pdf") {
    setLoading(format);
    setError(null);
    try {
      await exporter.download(format);
    } catch {
      setError(`Failed to export as ${format}`);
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="flex flex-wrap gap-3 items-center">
      {(["json", "markdown", "pdf"] as const).map((fmt) => (
        <button
          key={fmt}
          onClick={() => void handleExport(fmt)}
          disabled={loading !== null}
          className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 disabled:opacity-50 border border-gray-200 rounded-xl text-sm text-gray-900 transition focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          {loading === fmt ? (
            <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          ) : (
            <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
          )}
          <span>{fmt.toUpperCase()}</span>
        </button>
      ))}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}

// ─── Main OutcomePage ──────────────────────────────────────────────────────

export default function OutcomePage() {
  const { sessionId } = useParams({ from: "/sessions/$sessionId/outcome" });
  const navigate = useNavigate();
  const [transcriptOpen, setTranscriptOpen] = useState(false);

  const { data: session, isLoading: sessionLoading } = useSession(sessionId);
  const { data: outcome, isLoading: outcomeLoading } = useSessionOutcome(sessionId);
  const { data: messages = [], isLoading: messagesLoading } = useSessionMessages(sessionId);
  const { data: sources = [] } = useSessionSources(sessionId);
  const { data: votes = [] } = useSessionVotes(sessionId);
  const { data: auditEvents = [] } = useSessionAudit(sessionId);

  const isLoading = sessionLoading || outcomeLoading || messagesLoading;
  const seats = session?.panel_snapshot_json?.seats ?? [];

  const agentVotes = votes.filter((v) => v.voter_type === "agent");
  const humanVotes = votes.filter((v) => v.voter_type === "human");

  // Vote breakdown for donut charts
  function buildSlices(voteList: Vote[]) {
    const yes = voteList.filter((v) => v.vote === "yes").length;
    const no = voteList.filter((v) => v.vote === "no").length;
    const abstain = voteList.filter((v) => v.vote === "abstain").length;
    return [
      { value: yes, color: "#10b981", label: "Yes" },
      { value: no, color: "#ef4444", label: "No" },
      { value: abstain, color: "#6b7280", label: "Abstain" },
    ].filter((s) => s.value > 0);
  }

  const divergenceNoted = outcome?.divergence_noted;

  function getSeatName(seatId: string | null | undefined) {
    if (!seatId) return "Unknown";
    return seats.find((s) => s.seat_id === seatId)?.display_name ?? seatId;
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <svg className="w-8 h-8 animate-spin text-indigo-500" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white text-gray-900">
      <AppNavbar />
      {/* Sub-header */}
      <header className="sticky top-[68px] z-10 border-b border-gray-200 bg-white/95 backdrop-blur px-6 py-3 flex items-center gap-4">
        <button
          onClick={() => void navigate({ to: "/" })}
          className="text-gray-500 hover:text-gray-700 transition"
          aria-label="Back to dashboard"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12h18M3 12l6-6M3 12l6 6" />
          </svg>
        </button>
        <div className="flex-1 min-w-0">
          <p className="text-xs text-gray-500">Outcome</p>
          <h1 className="text-sm font-semibold text-gray-900 truncate">
            {session?.topic ?? "Loading…"}
          </h1>
        </div>
        <ExportBar sessionId={sessionId} />
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8 space-y-8">

        {/* ① Recommendation Header */}
        <section aria-label="Outcome recommendation">
          {outcome ? (
            <div className="bg-white border border-gray-200 rounded-2xl p-7 shadow-lg">
              <div className="flex items-center gap-3 mb-4">
                <span
                  className={`px-3 py-1 rounded-full text-xs font-semibold ${
                    outcome.type === "recommendation"
                      ? "bg-indigo-50 text-indigo-700 border border-indigo-200"
                      : "bg-amber-50 text-amber-700 border border-amber-200"
                  }`}
                >
                  {outcome.type === "recommendation" ? "Consensus Recommendation" : "No Consensus Reached"}
                </span>
                {divergenceNoted && (
                  <span className="px-3 py-1 rounded-full text-xs font-semibold bg-orange-50 text-orange-700 border border-orange-200">
                    Human–Agent Divergence
                  </span>
                )}
              </div>
              <p className="text-xl font-semibold text-gray-900 leading-relaxed">
                {outcome.statement}
              </p>
            </div>
          ) : (
            <div className="bg-white border border-gray-200 rounded-2xl p-7">
              <p className="text-gray-500">Outcome not yet available.</p>
            </div>
          )}
        </section>

        {/* ② Vote Breakdown */}
        {votes.length > 0 && (
          <section aria-label="Vote breakdown">
            <h2 className="text-base font-semibold text-gray-900 mb-4">Vote Breakdown</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Agent votes donut */}
              <div className="bg-gray-50 border border-gray-200 rounded-2xl p-5 flex items-center gap-5">
                <DonutChart slices={buildSlices(agentVotes)} />
                <div>
                  <p className="text-sm font-medium text-gray-900 mb-2">Agent Votes</p>
                  {[
                    { label: "Yes", color: "bg-emerald-500", count: agentVotes.filter((v) => v.vote === "yes").length },
                    { label: "No", color: "bg-red-500", count: agentVotes.filter((v) => v.vote === "no").length },
                    { label: "Abstain", color: "bg-gray-500", count: agentVotes.filter((v) => v.vote === "abstain").length },
                  ].map((row) => (
                    <div key={row.label} className="flex items-center gap-2 text-xs text-gray-500 mb-1">
                      <span className={`w-2 h-2 rounded-full ${row.color} flex-shrink-0`} />
                      {row.label}: {row.count}
                    </div>
                  ))}
                </div>
              </div>

              {/* Human votes donut */}
              <div className="bg-gray-50 border border-gray-200 rounded-2xl p-5 flex items-center gap-5">
                <DonutChart slices={humanVotes.length > 0 ? buildSlices(humanVotes) : [{ value: 1, color: "#374151", label: "None" }]} />
                <div>
                  <p className="text-sm font-medium text-gray-900 mb-2">Human Votes</p>
                  {humanVotes.length === 0 ? (
                    <p className="text-xs text-gray-500">No human votes submitted</p>
                  ) : (
                    [
                      { label: "Yes", color: "bg-emerald-500", count: humanVotes.filter((v) => v.vote === "yes").length },
                      { label: "No", color: "bg-red-500", count: humanVotes.filter((v) => v.vote === "no").length },
                      { label: "Abstain", color: "bg-gray-500", count: humanVotes.filter((v) => v.vote === "abstain").length },
                    ].map((row) => (
                      <div key={row.label} className="flex items-center gap-2 text-xs text-gray-500 mb-1">
                        <span className={`w-2 h-2 rounded-full ${row.color} flex-shrink-0`} />
                        {row.label}: {row.count}
                      </div>
                    ))
                  )}
                  {divergenceNoted && (
                    <p className="text-xs text-orange-400 mt-2">
                      Diverges from agent consensus
                    </p>
                  )}
                </div>
              </div>
            </div>
          </section>
        )}

        {/* ③ Supporting Arguments */}
        {outcome?.supporting_arguments && outcome.supporting_arguments.length > 0 && (
          <section aria-label="Supporting arguments">
            <h2 className="text-base font-semibold text-gray-900 mb-3">Key Supporting Arguments</h2>
            <div className="bg-gray-50 border border-gray-200 rounded-2xl p-5">
              <ul className="space-y-2.5">
                {outcome.supporting_arguments.map((arg, i) => (
                  <li key={i} className="flex gap-3 text-sm text-gray-700">
                    <span className="text-indigo-600 font-bold flex-shrink-0">{i + 1}.</span>
                    <span>{arg}</span>
                  </li>
                ))}
              </ul>
            </div>
          </section>
        )}

        {/* ④ Substantive Dissent */}
        {outcome?.substantive_dissents && outcome.substantive_dissents.length > 0 && (
          <section aria-label="Substantive dissent">
            <h2 className="text-base font-semibold text-gray-900 mb-3">Substantive Dissent</h2>
            <div className="space-y-3">
              {outcome.substantive_dissents.map((dissent, i) => (
                <details
                  key={i}
                  className="bg-white border border-amber-200 rounded-2xl overflow-hidden group"
                >
                  <summary className="flex items-center gap-3 px-5 py-3 cursor-pointer list-none hover:bg-amber-50/50 transition">
                    <svg className="w-4 h-4 text-amber-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <span className="text-sm text-amber-700 font-medium">Dissenting Position {i + 1}</span>
                  </summary>
                  <div className="px-5 pb-4 pt-2 border-t border-amber-200">
                    <p className="text-sm text-gray-700 leading-relaxed">{dissent}</p>
                  </div>
                </details>
              ))}
            </div>
          </section>
        )}

        {/* ⑤ Trust Signals */}
        {outcome && (
          <section aria-label="Trust signals">
            <h2 className="text-base font-semibold text-gray-900 mb-3">Trust Signals</h2>
            <div className="bg-gray-50 border border-gray-200 rounded-2xl p-5 flex flex-wrap gap-8 justify-center sm:justify-start">
              <ConfidenceGauge score={outcome.confidence_score} />
              <SourceDensityIndicator score={outcome.source_density_score} />
              <div className="flex flex-col items-center">
                <div className="w-[90px] h-[52px] flex items-center justify-center">
                  <span className="text-2xl font-bold text-indigo-600">{agentVotes.length}</span>
                </div>
                <span className="text-xs text-gray-500">Agent Votes</span>
              </div>
            </div>
          </section>
        )}

        {/* ⑥ Source Bibliography */}
        {sources.length > 0 && (
          <section aria-label="Source bibliography">
            <h2 className="text-base font-semibold text-gray-900 mb-3">
              Source Bibliography
              <span className="ml-2 text-xs text-gray-500 font-normal">({sources.length})</span>
            </h2>
            <div className="bg-gray-50 border border-gray-200 rounded-2xl divide-y divide-gray-200 overflow-hidden">
              {sources.map((src, i) => (
                <div key={src.id} className="flex gap-3 px-5 py-3">
                  <span className="text-xs text-gray-600 font-mono w-6 flex-shrink-0 pt-0.5">[{i + 1}]</span>
                  <div className="flex-1 min-w-0">
                    <a
                      href={src.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-indigo-600 hover:text-indigo-500 transition truncate block"
                    >
                      {src.title || src.url}
                    </a>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-xs text-gray-500 truncate">{src.domain}</span>
                      <span className="text-gray-700">·</span>
                      <span className="text-xs text-gray-600">
                        {new Date(src.retrieved_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* ⑦ Full Transcript */}
        <section aria-label="Full transcript">
          <button
            onClick={() => setTranscriptOpen((o) => !o)}
            className="flex items-center gap-2 text-base font-semibold text-gray-900 hover:text-gray-700 transition mb-3 focus:outline-none"
            aria-expanded={transcriptOpen}
          >
            Full Transcript
            <svg
              className={`w-4 h-4 text-gray-500 transition-transform ${transcriptOpen ? "rotate-180" : ""}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
            <span className="text-xs text-gray-600 font-normal ml-1">({messages.length} messages)</span>
          </button>

          {transcriptOpen && (
            <div className="bg-gray-50 border border-gray-200 rounded-2xl p-5">
              <TranscriptViewer messages={messages} seats={seats} />
            </div>
          )}
        </section>

        {/* ⑧ Agent Configurations */}
        {seats.length > 0 && (
          <section aria-label="Agent configurations">
            <h2 className="text-base font-semibold text-gray-900 mb-3">Agent Configurations</h2>
            <div className="bg-gray-50 border border-gray-200 rounded-2xl divide-y divide-gray-200 overflow-hidden">
              <div className="px-5 py-2.5 flex items-center gap-2">
                <span className="text-xs text-gray-400 font-medium">Panel:</span>
                <span className="text-xs text-gray-700">{session?.panel_snapshot_json?.name ?? "—"}</span>
              </div>
              {seats.map((seat) => (
                <details key={seat.seat_id} className="group">
                  <summary className="flex items-center gap-3 px-5 py-3 cursor-pointer list-none hover:bg-gray-100 transition">
                    <div
                      className="w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold"
                      style={{ backgroundColor: seat.color + "33", color: seat.color }}
                      aria-hidden
                    >
                      {seat.display_name.charAt(0)}
                    </div>
                    <span className="text-sm text-gray-700 flex-1">{seat.display_name}</span>
                    <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">{seat.model}</span>
                    <svg className="w-4 h-4 text-gray-600 group-open:rotate-180 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </summary>
                  <div className="px-5 pb-4 border-t border-gray-200">
                    <div className="text-xs text-gray-600 space-y-1 pt-3">
                      <p><span className="text-gray-500">Role:</span> {seat.persona.role}</p>
                      <p><span className="text-gray-500">Disposition:</span> {seat.persona.disposition}</p>
                      <p><span className="text-gray-500">Focus:</span> {seat.persona.domain_focus.join(", ")}</p>
                    </div>
                  </div>
                </details>
              ))}
            </div>
          </section>
        )}

        {/* ⑨ Participating Humans */}
        {humanVotes.length > 0 && (
          <section aria-label="Participating humans">
            <h2 className="text-base font-semibold text-gray-900 mb-3">Participating Humans</h2>
            <div className="bg-gray-50 border border-gray-200 rounded-2xl overflow-hidden">
              <table className="w-full text-sm" role="table">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left px-5 py-2.5 text-xs text-gray-500 font-medium">Participant</th>
                    <th className="text-left px-5 py-2.5 text-xs text-gray-500 font-medium">Vote</th>
                    <th className="text-left px-5 py-2.5 text-xs text-gray-500 font-medium">Rationale</th>
                  </tr>
                </thead>
                <tbody>
                  {humanVotes.map((v) => (
                    <tr key={v.id} className="border-b border-gray-200 last:border-0">
                      <td className="px-5 py-3 text-gray-700">{getSeatName(v.seat_id)}</td>
                      <td className="px-5 py-3">
                        <span
                          className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                            v.vote === "yes"
                              ? "bg-emerald-50 text-emerald-700"
                              : v.vote === "no"
                              ? "bg-red-50 text-red-700"
                              : "bg-gray-100 text-gray-600"
                          }`}
                        >
                          {v.vote.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-xs text-gray-500 max-w-xs truncate">{v.rationale || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {/* ⑩ Export Actions */}
        <section aria-label="Export actions">
          <h2 className="text-base font-semibold text-gray-900 mb-3">Export</h2>
          <div className="bg-gray-50 border border-gray-200 rounded-2xl p-5">
            <p className="text-xs text-gray-500 mb-3">
              Download a signed copy of the full discussion record. JSON bundles include an HMAC signature for tamper detection.
            </p>
            <ExportBar sessionId={sessionId} />
          </div>
        </section>

        {/* ⑪ Decision Outcome Tracking */}
        <section aria-label="Decision outcome tracking">
          <h2 className="text-base font-semibold text-gray-900 mb-3">Decision Outcome Tracking</h2>
          <div className="bg-gray-50 border border-gray-200 rounded-2xl p-5">
            <DecisionOutcomeTracker sessionId={sessionId} />
          </div>
        </section>

        {/* Audit log (collapsed) */}
        {auditEvents.length > 0 && (
          <section aria-label="Audit log">
            <details className="bg-gray-50 border border-gray-200 rounded-2xl overflow-hidden">
              <summary className="flex items-center gap-2 px-5 py-4 cursor-pointer list-none hover:bg-gray-100 transition text-sm font-medium text-gray-600">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Audit Log
                <span className="ml-auto text-xs text-gray-600">{auditEvents.length} events</span>
              </summary>
              <div className="border-t border-gray-200 max-h-64 overflow-y-auto">
                {auditEvents.map((evt) => (
                  <div key={evt.id} className="flex gap-4 px-5 py-2.5 border-b border-gray-200 last:border-0 hover:bg-gray-50">
                    <span className="text-xs text-gray-500 flex-shrink-0 font-mono">
                      {new Date(evt.created_at).toLocaleTimeString()}
                    </span>
                    <span className="text-xs text-gray-700 font-medium">{evt.event_type}</span>
                    <span className="text-xs text-gray-500">{evt.actor_type}</span>
                  </div>
                ))}
              </div>
            </details>
          </section>
        )}
      </main>
    </div>
  );
}
