import type { OrgSession } from "@/types/api";
import { Link } from "@tanstack/react-router";

interface SessionCardProps {
  session: OrgSession;
}

const statusColors: Record<string, string> = {
  draft: "bg-gray-100 text-gray-600",
  queued: "bg-yellow-50 text-yellow-700",
  running: "bg-green-50 text-green-700",
  paused: "bg-orange-50 text-orange-700",
  voting: "bg-purple-50 text-purple-700",
  concluded: "bg-blue-50 text-blue-700",
};

const phaseLabels: Record<string, string> = {
  opening: "Opening",
  exploration: "Exploration",
  debate: "Debate",
  convergence: "Convergence",
  vote: "Vote",
};

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatCost(cost: number): string {
  if (cost === 0) return "$0.00";
  return `$${cost.toFixed(2)}`;
}

export function SessionCard({ session }: SessionCardProps) {
  return (
    <Link
      to="/sessions/$sessionId"
      params={{ sessionId: session.id }}
      className="block bg-white hover:bg-gray-50 border border-gray-200 hover:border-gray-300 rounded-xl p-5 transition group"
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <h3 className="text-sm font-medium text-gray-900 group-hover:text-gray-900 line-clamp-2 leading-snug flex-1">
          {session.topic}
        </h3>
        <span
          className={`flex-shrink-0 text-xs font-medium px-2 py-0.5 rounded-full ${statusColors[session.status] ?? "bg-gray-100 text-gray-600"}`}
        >
          {session.status}
        </span>
      </div>

      <div className="flex items-center gap-3 text-xs text-gray-500">
        {session.phase && (
          <span className="text-gray-600">
            Phase: {phaseLabels[session.phase] ?? session.phase}
          </span>
        )}
        {session.panel_name && (
          <span className="text-gray-500 truncate">{session.panel_name}</span>
        )}
      </div>

      <div className="flex items-center justify-between mt-4 pt-3 border-t border-gray-200">
        <span className="text-xs text-gray-500">
          {formatDate(session.created_at)}
        </span>
        <span className="text-xs text-gray-500 font-mono">
          {formatCost(session.cost_actual)}
        </span>
      </div>
    </Link>
  );
}
