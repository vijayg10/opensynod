import { useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "@tanstack/react-router";
import { useSession, useSessionOutcome, useSessionVotes, useVote } from "@/hooks/useSessions";
import { useAuthStore } from "@/stores/auth-store";
import { useSessionStore } from "@/stores/session-store";
import { SSEClient } from "@/lib/sse-client";
import AppNavbar from "@/components/AppNavbar";
import type { SSEVoteUpdateEvent, VoteChoice, Vote } from "@/types/api";

const API_BASE = import.meta.env.VITE_API_URL ?? "";

const VOTE_LABELS: Record<VoteChoice, string> = {
  yes: "Yes — Recommend",
  no: "No — Reject",
  abstain: "Abstain",
};

const VOTE_COLORS: Record<VoteChoice, string> = {
  yes: "bg-emerald-600 hover:bg-emerald-500 border-emerald-500",
  no: "bg-red-700 hover:bg-red-600 border-red-600",
  abstain: "bg-gray-700 hover:bg-gray-600 border-gray-600",
};

const VOTE_CHIP_COLORS: Record<VoteChoice, string> = {
  yes: "bg-emerald-50 text-emerald-700 border border-emerald-200",
  no: "bg-red-50 text-red-700 border border-red-200",
  abstain: "bg-gray-100 text-gray-600 border border-gray-200",
};

function VoteChip({ vote }: { vote: VoteChoice }) {
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${VOTE_CHIP_COLORS[vote]}`}>
      {vote.toUpperCase()}
    </span>
  );
}

function TallyBar({ votes }: { votes: Vote[] }) {
  const yes = votes.filter((v) => v.vote === "yes").length;
  const no = votes.filter((v) => v.vote === "no").length;
  const abstain = votes.filter((v) => v.vote === "abstain").length;
  const total = votes.length || 1;

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3">
        <span className="text-xs text-gray-500 w-16">Yes</span>
        <div className="flex-1 bg-gray-200 rounded-full h-2 overflow-hidden">
          <div
            className="h-full bg-emerald-500 rounded-full transition-all duration-500"
            style={{ width: `${(yes / total) * 100}%` }}
          />
        </div>
        <span className="text-xs text-emerald-600 w-6 text-right">{yes}</span>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-xs text-gray-500 w-16">No</span>
        <div className="flex-1 bg-gray-200 rounded-full h-2 overflow-hidden">
          <div
            className="h-full bg-red-500 rounded-full transition-all duration-500"
            style={{ width: `${(no / total) * 100}%` }}
          />
        </div>
        <span className="text-xs text-red-600 w-6 text-right">{no}</span>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-xs text-gray-500 w-16">Abstain</span>
        <div className="flex-1 bg-gray-200 rounded-full h-2 overflow-hidden">
          <div
            className="h-full bg-gray-500 rounded-full transition-all duration-500"
            style={{ width: `${(abstain / total) * 100}%` }}
          />
        </div>
        <span className="text-xs text-gray-500 w-6 text-right">{abstain}</span>
      </div>
    </div>
  );
}

export default function VotingPage() {
  const { sessionId } = useParams({ from: "/sessions/$sessionId/vote" });
  const navigate = useNavigate();
  const accessToken = useAuthStore((s) => s.accessToken);
  const { addLiveVote, liveVotes } = useSessionStore();

  const { data: session, isLoading: sessionLoading } = useSession(sessionId);
  const { data: outcome, isLoading: outcomeLoading } = useSessionOutcome(sessionId);
  const { data: dbVotes, isLoading: votesLoading } = useSessionVotes(sessionId);
  const voteMutation = useVote(sessionId);

  const [selectedVote, setSelectedVote] = useState<VoteChoice | null>(null);
  const [rationale, setRationale] = useState("");
  const [hasVoted, setHasVoted] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const sseRef = useRef<SSEClient | null>(null);

  // Subscribe to live vote_update events
  useEffect(() => {
    if (!accessToken || !sessionId) return;
    const sseUrl = `${API_BASE}/api/v1/sessions/${sessionId}/stream`;
    const sse = new SSEClient(sseUrl, accessToken);

    sse.on("vote_update", (e: MessageEvent) => {
      const data = JSON.parse(e.data) as SSEVoteUpdateEvent;
      addLiveVote({
        voterId: data.voter_id,
        voterType: data.voter_type,
        voterName: data.voter_name,
        seatId: data.seat_id,
        vote: data.vote,
        rationale: data.rationale,
      });
    });

    sse.on("session_state", (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data) as { status?: string };
        if (data.status === "concluded") {
          void navigate({ to: "/sessions/$sessionId/outcome", params: { sessionId } });
        }
      } catch {
        // ignore parse errors
      }
    });

    sse.connect();
    sseRef.current = sse;

    return () => {
      sse.close();
      sseRef.current = null;
    };
  }, [sessionId, accessToken]); // eslint-disable-line react-hooks/exhaustive-deps

  // Merge DB votes + live votes (DB is authoritative; live fills gaps)
  const allVotes: Vote[] = dbVotes ?? [];
  const agentVotes = allVotes.filter((v) => v.voter_type === "agent");
  const humanVotes = allVotes.filter((v) => v.voter_type === "human");

  // Live votes from SSE (for progressive display before DB refresh)
  const liveAgentVotes = liveVotes.filter((v) => v.voterType === "agent");
  const allDisplayedAgentVotes = [
    ...agentVotes,
    ...liveAgentVotes.filter(
      (lv) => !agentVotes.some((dv) => dv.voter_id === lv.voterId)
    ).map((lv) => ({
      id: `live-${lv.voterId}`,
      session_id: sessionId,
      voter_id: lv.voterId,
      voter_type: "agent" as const,
      seat_id: lv.seatId,
      vote: lv.vote,
      rationale: lv.rationale ?? "",
      submitted_at: new Date().toISOString(),
    })),
  ];

  const isLoading = sessionLoading || outcomeLoading || votesLoading;

  const seats = session?.panel_snapshot_json?.seats ?? [];

  function getSeatName(seatId: string | null | undefined) {
    if (!seatId) return "Agent";
    const seat = seats.find((s) => s.seat_id === seatId);
    return seat?.display_name ?? seatId;
  }

  async function handleSubmitVote() {
    if (!selectedVote) return;
    setSubmitError(null);
    try {
      await voteMutation.mutateAsync({ vote: selectedVote, rationale });
      setHasVoted(true);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Failed to submit vote");
    }
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
          onClick={() => void navigate({ to: "/sessions/$sessionId", params: { sessionId } })}
          className="text-gray-500 hover:text-gray-700 transition"
          aria-label="Back to session"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <div className="flex-1 min-w-0">
          <p className="text-xs text-indigo-600 font-medium uppercase tracking-wide">Voting Phase</p>
          <h1 className="text-sm font-semibold text-gray-900 truncate">{session?.topic ?? ""}</h1>
        </div>
        <span className="text-xs bg-yellow-50 text-yellow-700 border border-yellow-300 px-2 py-0.5 rounded-full font-medium">
          Voting Open
        </span>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8 space-y-8">
        {/* Recommendation Card */}
        {outcome ? (
          <section
            className="bg-white border border-gray-200 rounded-2xl p-6 shadow-lg"
            aria-label="Proposed recommendation"
          >
            <div className="flex items-center gap-2 mb-3">
              <span
                className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${
                  outcome.type === "recommendation"
                    ? "bg-indigo-50 text-indigo-700 border border-indigo-200"
                    : "bg-gray-100 text-gray-600 border border-gray-200"
                }`}
              >
                {outcome.type === "recommendation" ? "Recommendation" : "No Consensus"}
              </span>
            </div>
            <p className="text-lg font-semibold text-gray-900 leading-relaxed mb-5">
              {outcome.statement}
            </p>

            {/* Supporting arguments */}
            {outcome.supporting_arguments?.length > 0 && (
              <div className="mb-4">
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                  Supporting Arguments
                </h3>
                <ul className="space-y-1.5">
                  {outcome.supporting_arguments.map((arg, i) => (
                    <li key={i} className="flex gap-2 text-sm text-gray-600">
                      <span className="text-indigo-600 mt-0.5 flex-shrink-0">•</span>
                      <span>{arg}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Substantive dissents */}
            {outcome.substantive_dissents?.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                  Substantive Dissent
                </h3>
                <ul className="space-y-1.5">
                  {outcome.substantive_dissents.map((d, i) => (
                    <li key={i} className="flex gap-2 text-sm text-amber-700">
                      <span className="text-amber-500 mt-0.5 flex-shrink-0">△</span>
                      <span>{d}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        ) : (
          <section className="bg-white border border-gray-200 rounded-2xl p-6">
            <p className="text-gray-500 text-sm">
              The moderator is preparing the recommendation…
            </p>
          </section>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Agent Vote Panel */}
          <section className="bg-gray-50 border border-gray-200 rounded-2xl p-5">
            <h2 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
              <svg className="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17H3a2 2 0 01-2-2V5a2 2 0 012-2h14a2 2 0 012 2v10a2 2 0 01-2 2h-2" />
              </svg>
              Agent Votes
              <span className="ml-auto text-xs text-gray-500">
                {allDisplayedAgentVotes.length} / {seats.length}
              </span>
            </h2>
            <div className="space-y-3">
              {seats.map((seat) => {
                const vote = allDisplayedAgentVotes.find(
                  (v) => v.seat_id === seat.seat_id || v.voter_id === seat.seat_id
                );
                return (
                  <div
                    key={seat.seat_id}
                    className="flex items-start gap-3 py-2 border-b border-gray-200 last:border-0"
                  >
                    <div
                      className="w-8 h-8 rounded-full flex items-center justify-center text-sm flex-shrink-0"
                      style={{ backgroundColor: seat.color + "33", color: seat.color }}
                      aria-hidden
                    >
                      {seat.display_name.charAt(0)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-sm text-gray-900 font-medium truncate">
                          {seat.display_name}
                        </span>
                        {vote ? (
                          <VoteChip vote={vote.vote} />
                        ) : (
                          <span className="text-xs text-gray-400 animate-pulse">Voting…</span>
                        )}
                      </div>
                      {vote?.rationale && (
                        <p className="text-xs text-gray-500 line-clamp-2">{vote.rationale}</p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Live tally */}
            {allVotes.length > 0 && (
              <div className="mt-4 pt-4 border-t border-gray-200">
                <p className="text-xs text-gray-500 mb-2">Running tally</p>
                <TallyBar votes={allVotes} />
              </div>
            )}
          </section>

          {/* Human Vote Panel */}
          <section className="bg-gray-50 border border-gray-200 rounded-2xl p-5">
            <h2 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
              <svg className="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
              Your Vote
            </h2>

            {/* Agent vote distribution first */}
            {allDisplayedAgentVotes.length > 0 && (
              <div className="mb-4 p-3 bg-gray-100 rounded-lg">
                <p className="text-xs text-gray-500 mb-2">Agent consensus so far</p>
                <TallyBar votes={allDisplayedAgentVotes} />
              </div>
            )}

            {hasVoted ? (
              <div className="text-center py-6">
                <div className="w-12 h-12 rounded-full bg-emerald-50 flex items-center justify-center mx-auto mb-3">
                  <svg className="w-6 h-6 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <p className="text-gray-700 font-medium">Vote submitted</p>
                {selectedVote && (
                  <VoteChip vote={selectedVote} />
                )}
                <p className="text-xs text-gray-500 mt-2">
                  Waiting for other participants…
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="grid grid-cols-3 gap-2">
                  {(["yes", "no", "abstain"] as VoteChoice[]).map((choice) => (
                    <button
                      key={choice}
                      onClick={() => setSelectedVote(choice)}
                      className={`py-3 px-2 rounded-xl text-sm font-medium border transition focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                        selectedVote === choice
                          ? VOTE_COLORS[choice] + " text-white"
                          : "border-gray-300 text-gray-500 hover:border-gray-400 hover:text-gray-700"
                      }`}
                      aria-pressed={selectedVote === choice}
                    >
                      {VOTE_LABELS[choice]}
                    </button>
                  ))}
                </div>

                <div>
                  <label
                    htmlFor="vote-rationale"
                    className="block text-xs text-gray-500 mb-1.5"
                  >
                    Rationale (optional)
                  </label>
                  <textarea
                    id="vote-rationale"
                    value={rationale}
                    onChange={(e) => setRationale(e.target.value)}
                    rows={3}
                    placeholder="Explain your reasoning…"
                    className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-900 placeholder-gray-400 resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  />
                </div>

                {submitError && (
                  <p className="text-xs text-red-600">{submitError}</p>
                )}

                <button
                  onClick={() => void handleSubmitVote()}
                  disabled={!selectedVote || voteMutation.isPending}
                  className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-xl transition focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  {voteMutation.isPending ? "Submitting…" : "Submit Vote"}
                </button>
              </div>
            )}

            {/* Other human votes */}
            {humanVotes.length > 0 && (
              <div className="mt-4 pt-4 border-t border-gray-200">
                <p className="text-xs text-gray-500 mb-2">
                  Human votes ({humanVotes.length})
                </p>
                <div className="space-y-1.5">
                  {humanVotes.map((v) => (
                    <div key={v.id} className="flex items-center gap-2">
                      <div className="w-5 h-5 rounded-full bg-gray-200 flex items-center justify-center text-xs text-gray-600 flex-shrink-0">
                        H
                      </div>
                      <span className="text-xs text-gray-500 truncate flex-1">
                        {getSeatName(v.seat_id) ?? "Human"}
                      </span>
                      <VoteChip vote={v.vote} />
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>
        </div>

        {/* Review transcript accordion */}
        <ReviewTranscriptAccordion sessionId={sessionId} />

        {/* Navigate to outcome when done */}
        {session?.status === "concluded" && (
          <div className="text-center">
            <button
              onClick={() =>
                void navigate({ to: "/sessions/$sessionId/outcome", params: { sessionId } })
              }
              className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-xl transition"
            >
              View Outcome →
            </button>
          </div>
        )}
      </main>
    </div>
  );
}

function ReviewTranscriptAccordion({ sessionId }: { sessionId: string }) {
  const [open, setOpen] = useState(false);

  return (
    <section className="bg-gray-50 border border-gray-200 rounded-2xl overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-5 py-4 text-sm font-medium text-gray-700 hover:bg-gray-100 transition"
        aria-expanded={open}
      >
        <span>Review discussion transcript</span>
        <svg
          className={`w-4 h-4 text-gray-500 transition-transform ${open ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && (
        <div className="px-5 pb-5 border-t border-gray-200">
          <p className="text-sm text-gray-500 pt-4">
            Full transcript is available on the{" "}
            <a
              href={`/sessions/${sessionId}`}
              className="text-indigo-600 hover:text-indigo-500 transition underline"
            >
              session page
            </a>
            .
          </p>
        </div>
      )}
    </section>
  );
}
