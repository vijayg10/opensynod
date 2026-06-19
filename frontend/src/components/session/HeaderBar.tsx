import { Link } from "@tanstack/react-router";
import type { Session } from "@/types/api";

interface HeaderBarProps {
  session: Session;
  elapsed: number; // seconds
  costActual: number;
}

const phaseLabels: Record<string, string> = {
  opening: "Opening",
  exploration: "Exploration",
  debate: "Debate",
  convergence: "Convergence",
  vote: "Vote",
};

const statusColors: Record<string, string> = {
  running: "bg-green-100 text-green-700",
  paused: "bg-orange-100 text-orange-700",
  voting: "bg-purple-100 text-purple-700",
  concluded: "bg-blue-100 text-blue-700",
  queued: "bg-yellow-100 text-yellow-700",
  draft: "bg-gray-100 text-gray-600",
  failed: "bg-red-100 text-red-700",
};

function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export function HeaderBar({ session, elapsed, costActual }: HeaderBarProps) {
  return (
    <header className="border-b border-gray-200 bg-white px-4 py-3 flex items-center gap-4">
      <Link to="/" className="text-gray-500 hover:text-gray-900 transition flex-shrink-0">
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
      </Link>

      {/* Topic */}
      <div className="flex-1 min-w-0">
        <h1 className="text-sm font-semibold text-gray-900 truncate">{session.topic}</h1>
        <div className="flex items-center gap-2 mt-0.5">
          {session.phase && (
            <span className="text-xs text-indigo-400">
              {phaseLabels[session.phase] ?? session.phase}
            </span>
          )}
          <span
            className={`text-xs font-medium px-1.5 py-0.5 rounded-full ${
              statusColors[session.status] ?? "bg-gray-100 text-gray-600"
            }`}
          >
            {session.status}
          </span>
        </div>
      </div>

      {/* Stats */}
      <div className="hidden sm:flex items-center gap-4 flex-shrink-0">
        {/* Timer */}
        <div className="text-right">
          <p className="text-xs text-gray-500">Elapsed</p>
          <p className="text-sm font-mono text-gray-900">{formatElapsed(elapsed)}</p>
        </div>

        {/* Cost */}
        <div className="text-right">
          <p className="text-xs text-gray-500">Cost</p>
          <p className="text-sm font-mono text-gray-900">${costActual.toFixed(4)}</p>
        </div>

        {/* Outcome type */}
        <div className="text-right">
          <p className="text-xs text-gray-500">Goal</p>
          <p className="text-sm text-gray-900 capitalize">{session.outcome_type}</p>
        </div>
      </div>
    </header>
  );
}
