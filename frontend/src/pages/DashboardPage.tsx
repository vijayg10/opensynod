import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { useOrgSessions } from "@/hooks/useSessions";
import { usePanels } from "@/hooks/usePanels";
import { SessionCard } from "@/components/dashboard/SessionCard";
import AppNavbar from "@/components/AppNavbar";
import type { SessionStatus } from "@/types/api";

const STATUS_TABS: { label: string; value: SessionStatus | "all" }[] = [
  { label: "All", value: "all" },
  { label: "Running", value: "running" },
  { label: "Paused", value: "paused" },
  { label: "Voting", value: "voting" },
  { label: "Concluded", value: "concluded" },
  { label: "Draft", value: "draft" },
];

export default function DashboardPage() {
  const [statusFilter, setStatusFilter] = useState<SessionStatus | "all">("all");

  const { data: sessionsData, isLoading: sessionsLoading } = useOrgSessions(
    statusFilter !== "all" ? { status: statusFilter } : undefined
  );
  const { data: panels, isLoading: panelsLoading } = usePanels();

  return (
    <div className="min-h-screen bg-white text-gray-900">
      <AppNavbar />
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Hero / CTA */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Discussions</h1>
            <p className="text-gray-500 text-sm mt-1">
              Orchestrate AI panel debates on any topic
            </p>
          </div>
          <Link
            to="/sessions/new/topic"
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-white"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Start Discussion
          </Link>
        </div>

        {/* Status Tabs */}
        <div className="flex gap-1 mb-6 border-b border-gray-200">
          {STATUS_TABS.map((tab) => (
            <button
              key={tab.value}
              onClick={() => setStatusFilter(tab.value)}
              className={`px-4 py-2 text-sm font-medium rounded-t-md transition -mb-px border-b-2 ${
                statusFilter === tab.value
                  ? "text-indigo-600 border-indigo-500"
                  : "text-gray-500 border-transparent hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Session List */}
        <section className="mb-12">
          {sessionsLoading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="bg-gray-50 border border-gray-200 rounded-xl p-5 animate-pulse">
                  <div className="h-4 bg-gray-200 rounded mb-3 w-3/4" />
                  <div className="h-3 bg-gray-200 rounded mb-2 w-1/2" />
                  <div className="h-3 bg-gray-200 rounded w-1/3 mt-4" />
                </div>
              ))}
            </div>
          ) : sessionsData?.length === 0 ? (
            <div className="text-center py-16 border border-dashed border-gray-300 rounded-xl">
              <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-4">
                <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
              </div>
              <p className="text-gray-500 text-sm">No discussions yet</p>
              <Link
                to="/sessions/new/topic"
                className="mt-3 inline-block text-indigo-600 hover:text-indigo-500 text-sm transition"
              >
                Start your first discussion →
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {sessionsData?.map((session) => (
                <SessionCard key={session.id} session={session} />
              ))}
            </div>
          )}
        </section>

        {/* Panel Gallery Teaser */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Panel Templates</h2>
            <Link
              to="/sessions/new/panel"
              className="text-sm text-indigo-600 hover:text-indigo-500 transition"
            >
              Browse all →
            </Link>
          </div>

          {panelsLoading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="bg-gray-50 border border-gray-200 rounded-xl p-4 animate-pulse">
                  <div className="h-4 bg-gray-200 rounded mb-2 w-2/3" />
                  <div className="h-3 bg-gray-200 rounded mb-1 w-full" />
                  <div className="h-3 bg-gray-200 rounded w-4/5" />
                </div>
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {panels?.slice(0, 4).map((panel) => (
                <Link
                  key={panel.id}
                  to="/sessions/new/panel"
                  className="block bg-white hover:bg-gray-50 border border-gray-200 hover:border-gray-300 rounded-xl p-4 transition group"
                >
                  <h3 className="text-sm font-medium text-gray-900 group-hover:text-gray-900 mb-1.5 line-clamp-1">
                    {panel.name}
                  </h3>
                  <p className="text-xs text-gray-500 line-clamp-2 leading-relaxed">
                    {panel.description}
                  </p>
                  <div className="mt-3 flex items-center gap-1">
                    <span className="text-xs text-gray-500">
                      {panel.seats.length} seats
                    </span>
                    {panel.is_system && (
                      <span className="ml-auto text-xs bg-indigo-50 text-indigo-600 px-1.5 py-0.5 rounded">
                        System
                      </span>
                    )}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
