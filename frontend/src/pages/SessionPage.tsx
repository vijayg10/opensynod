import { useEffect, useRef, useState, useCallback } from "react";
import { useParams, useNavigate } from "@tanstack/react-router";
import { useSession, useStartSession } from "@/hooks/useSessions";
import { useSessionStore } from "@/stores/session-store";
import { useAuthStore } from "@/stores/auth-store";
import { SSEClient } from "@/lib/sse-client";
import { refreshToken } from "@/lib/api";
import { WSClient } from "@/lib/ws-client";
import { HeaderBar } from "@/components/session/HeaderBar";
import { RoundTable } from "@/components/session/RoundTable";
import { SessionControls } from "@/components/session/SessionControls";
import { SidePanel } from "@/components/session/SidePanel";
import { LateJoinerOverlay } from "@/components/session/LateJoinerOverlay";
import type {
  SSETokenEvent,
  SSEMessageEvent,
  SSESpeakerEvent,
  SSECostEvent,
  SSEThemeEvent,
  SSESourceEvent,
  SSEVoteUpdateEvent,
} from "@/types/api";
import type { Message, Source } from "@/stores/session-store";

const API_BASE = import.meta.env.VITE_API_URL ?? "";

function getWsBase(): string {
  const base = API_BASE || window.location.origin;
  return base.replace(/^http/, "ws");
}

export default function SessionPage() {
  const { sessionId } = useParams({ from: "/sessions/$sessionId" });
  const navigate = useNavigate();
  const accessToken = useAuthStore((s) => s.accessToken);

  const {
    messages,
    sessionStatus,
    currentPhase,
    currentSpeaker,
    sources,
    costActual,
    themes,
    setSessionId,
    setSessionStatus,
    appendMessage,
    appendToken,
    finalizeMessage,
    setPhase,
    setCurrentSpeaker,
    addSource,
    updateCost,
    setThemes,
    addLiveVote,
    reset,
  } = useSessionStore();

  const { data: session, isLoading, error } = useSession(sessionId);
  const startSession = useStartSession(sessionId);

  // Poll session status while queued — catches failures if SSE misses them
  useEffect(() => {
    const effectiveStatus = sessionStatus || session?.status;
    if (!effectiveStatus || !["queued"].includes(effectiveStatus)) return;
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/v1/sessions/${sessionId}`, {
          headers: { Authorization: `Bearer ${accessToken}` },
        });
        if (res.ok) {
          const data = await res.json();
          if (data.status === "failed") {
            setSessionStatus("failed");
            setStartRequested(false);
          } else if (data.status === "running") {
            setSessionStatus("running");
          }
        }
      } catch { /* ignore */ }
    }, 3000);
    return () => clearInterval(interval);
  }, [sessionStatus, session?.status, sessionId, accessToken]); // eslint-disable-line react-hooks/exhaustive-deps

  // Redirect to vote page if session is already in voting status
  const resolvedStatus = sessionStatus || session?.status;
  useEffect(() => {
    if (resolvedStatus === "voting") {
      void navigate({ to: "/sessions/$sessionId/vote", params: { sessionId } });
    } else if (resolvedStatus === "concluded") {
      void navigate({ to: "/sessions/$sessionId/outcome", params: { sessionId } });
    }
  }, [resolvedStatus]); // eslint-disable-line react-hooks/exhaustive-deps

  const sseRef = useRef<SSEClient | null>(null);
  const wsRef = useRef<WSClient | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [showLateJoiner, setShowLateJoiner] = useState(false);
  const [lateJoinerDismissed, setLateJoinerDismissed] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const connectedRef = useRef(false);

  // Reset store when sessionId changes
  useEffect(() => {
    reset();
    setSessionId(sessionId);
    connectedRef.current = false;
    return () => {
      reset();
    };
  }, [sessionId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Elapsed timer
  useEffect(() => {
    if (resolvedStatus === "running") {
      if (timerRef.current) clearInterval(timerRef.current);
      // Compute initial elapsed from started_at
      const startedAt = session?.started_at ? new Date(session.started_at).getTime() : Date.now();
      const updateElapsed = () => {
        setElapsed(Math.floor((Date.now() - startedAt) / 1000));
      };
      updateElapsed();
      timerRef.current = setInterval(updateElapsed, 1000);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [resolvedStatus, session?.started_at]);

  // Connect SSE + WS once session is loaded
  useEffect(() => {
    if (!session || !accessToken || connectedRef.current) return;
    if (!["running", "paused", "voting", "queued"].includes(session.status)) return;

    connectedRef.current = true;

    // SSE — use a getter so reconnects always use the latest token after refresh
    const sseUrl = `${API_BASE}/api/v1/sessions/${sessionId}/stream`;
    const sse = new SSEClient(
      sseUrl,
      () => useAuthStore.getState().accessToken,
      {
        onTokenExpired: async () => {
          const newToken = await refreshToken();
          if (newToken) {
            useAuthStore.getState().setToken(newToken);
          }
          return newToken;
        },
      },
    );

    sse.on("session_state", (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      if (data.status) setSessionStatus(data.status);
      if (data.phase) setPhase(data.phase);
      if (data.cost_actual != null) updateCost(data.cost_actual, data.cost_limit ?? null);
      if (data.status === "failed" && data.error) {
        setErrorMsg(data.error);
      }
    });

    sse.on("token", (e: MessageEvent) => {
      const data = JSON.parse(e.data) as SSETokenEvent;
      appendToken(data.message_id, data.token);
    });

    sse.on("message_start", (e: MessageEvent) => {
      const data = JSON.parse(e.data) as SSEMessageEvent;
      const msg: Message = {
        id: data.message_id,
        sessionId: data.session_id,
        seatId: data.seat_id,
        authorType: data.author_type,
        content: "",
        model: null,
        phase: data.phase,
        createdAt: new Date().toISOString(),
        streaming: true,
      };
      appendMessage(msg);
    });

    sse.on("message_end", (e: MessageEvent) => {
      const data = JSON.parse(e.data) as SSEMessageEvent;
      finalizeMessage(data.message_id);
    });

    sse.on("message", (e: MessageEvent) => {
      const data = JSON.parse(e.data) as SSEMessageEvent;
      const msg: Message = {
        id: data.message_id,
        sessionId: data.session_id,
        seatId: data.seat_id,
        authorType: data.author_type,
        content: data.content,
        model: null,
        phase: data.phase,
        createdAt: new Date().toISOString(),
        streaming: false,
      };
      appendMessage(msg);
    });

    sse.on("phase_change", (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      const phase = data.phase ?? data.to;
      if (phase) setPhase(phase);
      // Navigate automatically when voting phase begins
      if (phase === "vote") {
        void navigate({ to: "/sessions/$sessionId/vote", params: { sessionId } });
      }
    });

    sse.on("speaker_change", (e: MessageEvent) => {
      const data = JSON.parse(e.data) as SSESpeakerEvent;
      setCurrentSpeaker(data.seat_id);
    });

    sse.on("cost_update", (e: MessageEvent) => {
      const data = JSON.parse(e.data) as SSECostEvent;
      updateCost(data.cost_actual, data.cost_limit);
    });

    sse.on("theme_update", (e: MessageEvent) => {
      const data = JSON.parse(e.data) as SSEThemeEvent;
      setThemes(data.themes);
    });

    sse.on("source_ready", (e: MessageEvent) => {
      const data = JSON.parse(e.data) as SSESourceEvent;
      const src: Source = {
        id: data.source?.id ?? "",
        url: data.source?.url ?? "",
        title: data.source?.title ?? "",
        domain: data.source?.domain ?? "",
        retrievedAt: data.source?.retrieved_at ?? new Date().toISOString(),
        seatId: data.source?.retrieval_seat_id ?? null,
      };
      addSource(src);
    });

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

    sse.connect();
    sseRef.current = sse;

    // WebSocket
    const wsUrl = `${getWsBase()}/api/v1/sessions/${sessionId}/ws`;
    const ws = new WSClient(wsUrl, accessToken);

    ws.on("participant_joined", () => {
      // could update participants
    });

    ws.connect();
    wsRef.current = ws;

    return () => {
      sse.close();
      ws.close();
      sseRef.current = null;
      wsRef.current = null;
      connectedRef.current = false;
    };
  }, [session?.status, sessionId, accessToken]); // eslint-disable-line react-hooks/exhaustive-deps

  // Late joiner: show overlay if joining a running session with messages
  useEffect(() => {
    if (
      !lateJoinerDismissed &&
      session &&
      ["running", "paused"].includes(session.status) &&
      messages.length > 5
    ) {
      setShowLateJoiner(true);
    }
  }, [session?.status, messages.length, lateJoinerDismissed]); // eslint-disable-line react-hooks/exhaustive-deps

  const [startRequested, setStartRequested] = useState(false);

  const handleStartSession = useCallback(() => {
    setStartRequested(true);
    startSession.mutate();
  }, [startSession]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <svg className="w-8 h-8 animate-spin text-indigo-500 mx-auto mb-3" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <p className="text-gray-600 text-sm">Loading session...</p>
        </div>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 text-sm mb-4">{error?.message ?? "Session not found"}</p>
          <button
            onClick={() => void navigate({ to: "/" })}
            className="text-indigo-600 hover:text-indigo-500 text-sm transition"
          >
            ← Back to dashboard
          </button>
        </div>
      </div>
    );
  }

  const seats = session.panel_snapshot_json?.seats ?? [];
  const effectiveCost = costActual || session.cost_actual;
  const effectivePhase = (currentPhase || session.phase) as typeof session.phase;
  const effectiveStatus = sessionStatus || session.status;

  return (
    <div className="h-screen bg-white text-gray-900 flex flex-col overflow-hidden">
      {/* Header */}
      <HeaderBar
        session={{ ...session, status: effectiveStatus, phase: effectivePhase }}
        elapsed={elapsed}
        costActual={effectiveCost}
      />

      {/* Body */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Late Joiner Overlay */}
        {showLateJoiner && !lateJoinerDismissed && (
          <LateJoinerOverlay
            messageCount={messages.length}
            onCatchUp={() => {
              setShowLateJoiner(false);
              setLateJoinerDismissed(true);
            }}
            onJoinLive={() => {
              setShowLateJoiner(false);
              setLateJoinerDismissed(true);
            }}
          />
        )}

        {/* Left: Round Table + Transcript + Controls */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Draft/Queued: Show start button */}
          {(effectiveStatus === "draft" || effectiveStatus === "queued") && (
            <div className="flex-1 flex items-center justify-center flex-col gap-4 p-8">
              <RoundTable seats={seats} currentSpeaker={null} size={750} />
              <div className="text-center mt-4">
                <h2 className="text-lg font-semibold text-gray-900 mb-2">Ready to Start</h2>
                <p className="text-gray-600 text-sm mb-6 max-w-sm">
                  {session.topic}
                </p>
                <button
                  onClick={handleStartSession}
                  disabled={startRequested}
                  className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition flex items-center gap-2 mx-auto"
                >
                  {startRequested ? (
                    <>
                      <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      Setting up discussion...
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Start Discussion
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* Failed state */}
          {effectiveStatus === "failed" && (
            <div className="flex-1 flex items-center justify-center flex-col gap-4 p-8">
              <RoundTable seats={seats} currentSpeaker={null} size={750} />
              <div className="text-center mt-4">
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-red-100 mb-4">
                  <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                </div>
                <h2 className="text-lg font-semibold text-gray-900 mb-2">Discussion Failed</h2>
                <p className="text-gray-600 text-sm mb-4 max-w-sm">
                  Something went wrong while running the discussion. This could be due to an LLM provider outage or a configuration issue.
                </p>
                {(errorMsg || session?.error) && (
                  <div className="bg-red-50 text-red-800 text-xs font-mono p-3 rounded-lg max-w-md mx-auto mb-6 text-left border border-red-200 break-words whitespace-pre-wrap">
                    <strong>Error details:</strong>
                    <div className="mt-1">{errorMsg || session?.error}</div>
                  </div>
                )}
                <div className="flex gap-3 justify-center">
                  <button
                    onClick={() => {
                      setStartRequested(false);
                      void navigate({ to: "/" });
                    }}
                    className="px-5 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition"
                  >
                    Back to Dashboard
                  </button>
                  <button
                    onClick={() => {
                      setSessionStatus("queued");
                      setStartRequested(true);
                      setErrorMsg(null);
                      startSession.mutate();
                    }}
                    disabled={startSession.isPending}
                    className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 text-white text-sm font-medium rounded-lg transition flex items-center gap-2"
                  >
                    {startSession.isPending ? (
                      <>
                        <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        Retrying...
                      </>
                    ) : "Retry"}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Active session: table centered */}
          {(effectiveStatus === "running" || effectiveStatus === "paused" || effectiveStatus === "voting" || effectiveStatus === "concluded") && (
            <>
              <div className="flex-1 flex items-center justify-center bg-white">
                <RoundTable seats={seats} currentSpeaker={currentSpeaker} size={720} />
              </div>

              {/* Controls */}
              <SessionControls session={session} />
            </>
          )}
        </div>

        {/* Right: Side Panel */}
        <div className="w-[640px] flex-shrink-0 hidden xl:flex flex-col border-l border-gray-200">
          <SidePanel
            session={session}
            themes={themes}
            sources={sources}
            currentPhase={effectivePhase}
            messages={messages}
          />
        </div>
      </div>
    </div>
  );
}
