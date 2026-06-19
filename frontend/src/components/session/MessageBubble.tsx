import { useState } from "react";
import type { Message } from "@/stores/session-store";
import type { SeatConfig } from "@/types/api";

interface MessageBubbleProps {
  message: Message;
  seats: SeatConfig[];
}

const AUTHOR_STYLES: Record<string, { bg: string; border: string; label: string; labelColor: string }> = {
  agent: {
    bg: "bg-gray-50",
    border: "border-gray-200",
    label: "Agent",
    labelColor: "text-indigo-600",
  },
  moderator: {
    bg: "bg-indigo-50",
    border: "border-indigo-200",
    label: "Moderator",
    labelColor: "text-indigo-600",
  },
  human: {
    bg: "bg-blue-50",
    border: "border-blue-200",
    label: "You",
    labelColor: "text-blue-600",
  },
  system: {
    bg: "bg-gray-50",
    border: "border-gray-200",
    label: "System",
    labelColor: "text-gray-500",
  },
};

const SEAT_COLORS = [
  "text-indigo-400",
  "text-violet-400",
  "text-pink-400",
  "text-amber-400",
  "text-emerald-400",
  "text-blue-400",
  "text-red-400",
  "text-teal-400",
];

function formatTime(dateStr: string): string {
  return new Date(dateStr).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

export function MessageBubble({ message, seats }: MessageBubbleProps) {
  const style = AUTHOR_STYLES[message.authorType] ?? AUTHOR_STYLES.system;
  const [showThinking, setShowThinking] = useState(false);

  // Find seat for agent messages
  const seatIndex = seats.findIndex((s) => s.seat_id === message.seatId);
  const seat = seatIndex >= 0 ? seats[seatIndex] : null;
  const seatLabel = seat?.display_name ?? "";
  const seatColor = seatIndex >= 0 ? SEAT_COLORS[seatIndex % SEAT_COLORS.length] : "text-gray-400";

  const isSystem = message.authorType === "system";
  const isHuman = message.authorType === "human";

  if (isSystem) {
    return (
      <div className="flex justify-center my-2">
        <div className="text-xs text-gray-500 bg-gray-100 border border-gray-200 rounded-full px-3 py-1">
          {message.content}
        </div>
      </div>
    );
  }

  let thinkingContent: string | null = null;
  let cleanContent = message.content;

  if (message.content.includes("<think>")) {
    const parts = message.content.split("<think>");
    const afterThink = parts[1] || "";
    if (afterThink.includes("</think>")) {
      const subParts = afterThink.split("</think>");
      thinkingContent = subParts[0].trim();
      cleanContent = (parts[0] + subParts[1]).trim();
    } else {
      thinkingContent = afterThink.trim();
      cleanContent = parts[0].trim();
    }
  }

  const isStreamingThoughts = message.streaming && message.content.includes("<think>") && !message.content.includes("</think>");
  const isStreamingContent = message.streaming && (!message.content.includes("<think>") || message.content.includes("</think>"));

  return (
    <div className={`flex ${isHuman ? "justify-end" : "justify-start"} mb-3`}>
      <div
        className={`max-w-[85%] rounded-xl border px-4 py-3 ${style.bg} ${style.border}`}
        style={{ wordBreak: "break-word" }}
      >
        {/* Header */}
        <div className="flex items-center gap-2 mb-2">
          {seat ? (
            <span className={`text-xs font-semibold ${seatColor}`}>{seatLabel}</span>
          ) : (
            <span className={`text-xs font-semibold ${style.labelColor}`}>{style.label}</span>
          )}
          {message.model && (
            <span className="text-xs text-gray-400 font-mono">{message.model}</span>
          )}
          {message.phase && (
            <span className="text-xs text-gray-400 capitalize">{message.phase}</span>
          )}
          <span className="ml-auto text-xs text-gray-400 font-mono">
            {formatTime(message.createdAt)}
          </span>
        </div>

        {/* Thinking Process */}
        {thinkingContent !== null && (
          <div className="mb-3 border-l-2 border-gray-300 pl-3">
            <button
              onClick={() => setShowThinking(!showThinking)}
              className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 transition font-medium focus:outline-none"
            >
              <svg
                className={`w-3.5 h-3.5 transform transition-transform ${showThinking || isStreamingThoughts ? "rotate-90" : ""}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
              {isStreamingThoughts ? (
                <>
                  <svg className="w-3 h-3 animate-spin text-indigo-500" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Thinking...
                </>
              ) : (
                "Thought Process"
              )}
            </button>
            {(showThinking || isStreamingThoughts) && (
              <div className="mt-2 text-xs text-gray-500 font-mono bg-gray-100/50 rounded-lg p-2.5 max-h-60 overflow-y-auto whitespace-pre-wrap leading-relaxed">
                {thinkingContent}
                {isStreamingThoughts && (
                  <span className="inline-block w-1 h-3 bg-gray-400 ml-0.5 animate-pulse" />
                )}
              </div>
            )}
          </div>
        )}

        {/* Content */}
        {cleanContent || isStreamingContent ? (
          <p className="text-sm text-gray-900 leading-relaxed whitespace-pre-wrap">
            {cleanContent}
            {isStreamingContent && (
              <span className="inline-block w-0.5 h-3.5 bg-indigo-400 ml-0.5 animate-pulse align-middle" />
            )}
          </p>
        ) : null}
      </div>
    </div>
  );
}
