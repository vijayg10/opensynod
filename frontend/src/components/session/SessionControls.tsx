import { useState } from "react";
import {
  usePauseSession,
  useResumeSession,
  useEndSession,
  useSkipTurn,
  useIntervene,
} from "@/hooks/useSessions";
import type { Session } from "@/types/api";

interface SessionControlsProps {
  session: Session;
}

export function SessionControls({ session }: SessionControlsProps) {
  const [intervention, setIntervention] = useState("");
  const [showEndConfirm, setShowEndConfirm] = useState(false);

  const pauseMutation = usePauseSession(session.id);
  const resumeMutation = useResumeSession(session.id);
  const endMutation = useEndSession(session.id);
  const skipMutation = useSkipTurn(session.id);
  const interveneMutation = useIntervene(session.id);

  const isRunning = session.status === "running";
  const isPaused = session.status === "paused";
  const isConcluded = session.status === "concluded";
  const isVoting = session.status === "voting";
  const canIntervene =
    (session.discussion_rules_json?.allow_human_interventions !== false) && (isRunning || isPaused);

  const handleSendIntervention = () => {
    const content = intervention.trim();
    if (!content) return;
    interveneMutation.mutate(
      { content },
      {
        onSuccess: () => setIntervention(""),
      }
    );
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      handleSendIntervention();
    }
  };

  return (
    <div className="border-t border-gray-200 bg-white px-4 py-3 space-y-3">
      {/* Intervention Input */}
      {canIntervene && (
        <div className="flex gap-2 items-end">
          <div className="flex-1">
            <textarea
              value={intervention}
              onChange={(e) => setIntervention(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type an intervention... (Ctrl+Enter to send)"
              rows={2}
              className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 text-sm placeholder-gray-400 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition resize-none"
            />
          </div>
          <button
            onClick={handleSendIntervention}
            disabled={!intervention.trim() || interveneMutation.isPending}
            className="px-3 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition flex items-center gap-1.5"
          >
            {interveneMutation.isPending ? (
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            )}
            Send
          </button>
        </div>
      )}

      {/* Control Buttons */}
      {!isConcluded && (
        <div className="flex items-center gap-2 flex-wrap">
          {/* Pause / Resume */}
          {isRunning && (
            <button
              onClick={() => pauseMutation.mutate()}
              disabled={pauseMutation.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-orange-100 hover:bg-orange-200 disabled:opacity-40 text-orange-700 text-xs font-medium rounded-lg transition"
            >
              <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                <rect x="6" y="4" width="4" height="16" />
                <rect x="14" y="4" width="4" height="16" />
              </svg>
              Pause
            </button>
          )}

          {isPaused && (
            <button
              onClick={() => resumeMutation.mutate()}
              disabled={resumeMutation.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-green-100 hover:bg-green-200 disabled:opacity-40 text-green-700 text-xs font-medium rounded-lg transition"
            >
              <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z" />
              </svg>
              Resume
            </button>
          )}

          {/* Skip Turn */}
          {(isRunning || isVoting) && (
            <button
              onClick={() => skipMutation.mutate()}
              disabled={skipMutation.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 hover:bg-gray-200 disabled:opacity-40 text-gray-700 text-xs font-medium rounded-lg transition"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
              </svg>
              Skip Turn
            </button>
          )}

          {/* End Session */}
          {!showEndConfirm ? (
            <button
              onClick={() => setShowEndConfirm(true)}
              className="ml-auto flex items-center gap-1.5 px-3 py-1.5 bg-red-50 hover:bg-red-100 text-red-600 text-xs font-medium rounded-lg transition border border-red-200"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
              End Discussion
            </button>
          ) : (
            <div className="ml-auto flex items-center gap-2">
              <span className="text-xs text-red-600">Are you sure?</span>
              <button
                onClick={() => {
                  endMutation.mutate();
                  setShowEndConfirm(false);
                }}
                disabled={endMutation.isPending}
                className="px-3 py-1.5 bg-red-700 hover:bg-red-600 disabled:opacity-40 text-white text-xs font-medium rounded-lg transition"
              >
                End
              </button>
              <button
                onClick={() => setShowEndConfirm(false)}
                className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-medium rounded-lg transition"
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      )}

      {isConcluded && (
        <div className="text-center text-xs text-gray-500 py-1">
          Discussion concluded
        </div>
      )}
    </div>
  );
}
