import { useState, useRef, useEffect } from "react";
import type { Session, SeatConfig } from "@/types/api";
import type { Message, Source } from "@/stores/session-store";
import { MessageBubble } from "./MessageBubble";

interface SidePanelProps {
  session: Session;
  themes: string[];
  sources: Source[];
  currentPhase: string | null;
  messages?: Message[];
}

const PHASES = ["opening", "exploration", "debate", "convergence", "vote"];
const PHASE_LABELS: Record<string, string> = {
  opening: "Opening",
  exploration: "Exploration",
  debate: "Debate",
  convergence: "Convergence",
  vote: "Vote",
};

type TabKey = "chat" | "phases" | "themes" | "sources" | "seats";

export function SidePanel({ session, themes, sources, currentPhase, messages = [] }: SidePanelProps) {
  const [activeTab, setActiveTab] = useState<TabKey>("chat");
  const chatBottomRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const userScrolledUp = useRef(false);

  useEffect(() => {
    if (activeTab !== "chat" || messages.length === 0 || userScrolledUp.current) return;
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, messages[messages.length - 1]?.content.length, activeTab]);
  const seats: SeatConfig[] = session.panel_snapshot_json?.seats ?? [];

  const currentPhaseIndex = currentPhase ? PHASES.indexOf(currentPhase) : -1;

  return (
    <div className="flex flex-col bg-gray-50 border-l border-gray-200 h-full">
      {/* Tabs */}
      <div className="flex border-b border-gray-200">
        {(
          [
            { key: "chat" as const, label: "Chat" },
            { key: "phases" as const, label: "Phases" },
            { key: "themes" as const, label: "Themes" },
            { key: "sources" as const, label: "Sources" },
            { key: "seats" as const, label: "Seats" },
          ] as const
        ).map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex-1 py-2.5 text-xs font-medium transition border-b-2 ${
              activeTab === tab.key
                ? "text-indigo-600 border-indigo-500"
                : "text-gray-500 border-transparent hover:text-gray-900"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Chat Tab — simple scrolling list, no virtualizer */}
      {activeTab === "chat" && (
        <div
          ref={chatContainerRef}
          className="flex-1 overflow-y-auto px-3 py-3"
          onScroll={() => {
            const el = chatContainerRef.current;
            if (!el) return;
            userScrolledUp.current = el.scrollHeight - el.scrollTop - el.clientHeight > 60;
          }}
        >
          {messages.length === 0 ? (
            <p className="text-xs text-gray-500 text-center py-6">
              Discussion has not started yet
            </p>
          ) : (
            messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} seats={seats} />
            ))
          )}
          <div ref={chatBottomRef} />
        </div>
      )}

      {/* Content */}
      <div className={`flex-1 overflow-y-auto p-4 ${activeTab === "chat" ? "hidden" : ""}`}>
        {/* Phases Tab */}
        {activeTab === "phases" && (
          <div className="space-y-2">
            {PHASES.map((phase, i) => {
              const isActive = phase === currentPhase;
              const isDone = currentPhaseIndex > i;
              return (
                <div
                  key={phase}
                  className={`flex items-center gap-3 p-3 rounded-lg ${
                    isActive
                      ? "bg-indigo-50 border border-indigo-200"
                      : isDone
                      ? "bg-gray-100 opacity-60"
                      : "bg-gray-100 opacity-40"
                  }`}
                >
                  <div
                    className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold ${
                      isActive
                        ? "bg-indigo-600 text-white"
                        : isDone
                        ? "bg-gray-300 text-gray-600"
                        : "bg-gray-200 text-gray-500"
                    }`}
                  >
                    {isDone ? (
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                      </svg>
                    ) : (
                      i + 1
                    )}
                  </div>
                  <div>
                    <p className={`text-xs font-medium ${isActive ? "text-indigo-700" : "text-gray-600"}`}>
                      {PHASE_LABELS[phase]}
                    </p>
                    {isActive && (
                      <p className="text-xs text-indigo-600 mt-0.5 flex items-center gap-1">
                        <span className="inline-block w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                        In progress
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Themes Tab */}
        {activeTab === "themes" && (
          <div>
            {themes.length === 0 ? (
              <p className="text-xs text-gray-500 text-center py-6">
                Themes will appear as the discussion progresses
              </p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {themes.map((theme, i) => (
                  <span
                    key={i}
                    className="text-xs bg-white text-gray-700 border border-gray-200 px-2.5 py-1 rounded-full"
                  >
                    {theme}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Sources Tab */}
        {activeTab === "sources" && (
          <div className="space-y-2">
            {sources.length === 0 ? (
              <p className="text-xs text-gray-500 text-center py-6">
                No sources cited yet
              </p>
            ) : (
              sources.map((source) => (
                <a
                  key={source.id}
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block bg-white hover:bg-gray-100 border border-gray-200 rounded-lg p-3 transition group"
                >
                  <p className="text-xs font-medium text-gray-700 group-hover:text-gray-900 line-clamp-2 mb-1">
                    {source.title || source.url}
                  </p>
                  <p className="text-xs text-gray-500">{source.domain}</p>
                </a>
              ))
            )}
          </div>
        )}

        {/* Seats Tab */}
        {activeTab === "seats" && (
          <div className="space-y-2">
            {seats.length === 0 ? (
              <p className="text-xs text-gray-500 text-center py-6">No seat data</p>
            ) : (
              seats.map((seat: SeatConfig) => {
                const seatKey: string = seat.seat_id;
                const seatName: string = seat.display_name;
                return (
                  <div
                    key={seatKey}
                    className="flex items-center gap-2.5 p-3 bg-white border border-gray-200 rounded-lg"
                  >
                    <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center flex-shrink-0">
                      <span className="text-xs font-bold text-indigo-600">
                        {seatName.charAt(0).toUpperCase()}
                      </span>
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-medium text-gray-900 leading-tight">{seatName}</p>
                      <p className="text-xs text-gray-500 truncate">{seat.model}</p>
                    </div>
                  </div>
                );
              })
            )}

            {/* Moderator */}
            {session.panel_snapshot_json?.moderator_config && (
              <div className="mt-3">
                <p className="text-xs text-gray-500 mb-2 uppercase tracking-wider">Moderator</p>
                <div className="flex items-center gap-2.5 p-3 bg-indigo-50 border border-indigo-200 rounded-lg">
                  <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center flex-shrink-0">
                    <svg className="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-indigo-700">Moderator</p>
                    <p className="text-xs text-indigo-600">
                      {session.panel_snapshot_json.moderator_config.model}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
