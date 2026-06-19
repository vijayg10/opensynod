interface LateJoinerOverlayProps {
  onCatchUp: () => void;
  onJoinLive: () => void;
  messageCount: number;
}

export function LateJoinerOverlay({ onCatchUp, onJoinLive, messageCount }: LateJoinerOverlayProps) {
  return (
    <div className="absolute inset-0 z-20 bg-gray-900/60 backdrop-blur-sm flex items-center justify-center px-4">
      <div className="bg-white border border-gray-200 rounded-2xl p-8 max-w-sm w-full text-center shadow-2xl">
        {/* Icon */}
        <div className="w-14 h-14 rounded-full bg-indigo-100 flex items-center justify-center mx-auto mb-5">
          <svg className="w-7 h-7 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>

        <h2 className="text-lg font-semibold text-gray-900 mb-2">
          Discussion In Progress
        </h2>
        <p className="text-sm text-gray-600 mb-6">
          There {messageCount === 1 ? "is" : "are"} already{" "}
          <span className="text-gray-900 font-medium">{messageCount}</span>{" "}
          {messageCount === 1 ? "message" : "messages"} in this discussion.
          Would you like to catch up first?
        </p>

        <div className="space-y-3">
          <button
            onClick={onCatchUp}
            className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-white"
          >
            Catch Up from Beginning
          </button>
          <button
            onClick={onJoinLive}
            className="w-full py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium rounded-lg transition"
          >
            Join Live (Skip History)
          </button>
        </div>
      </div>
    </div>
  );
}
