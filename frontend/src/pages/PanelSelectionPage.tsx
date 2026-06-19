import { useState } from "react";
import { useNavigate, Link } from "@tanstack/react-router";
import { usePanels } from "@/hooks/usePanels";
import { useNewSessionStore } from "@/stores/new-session-store";
import AppNavbar from "@/components/AppNavbar";
import type { Panel, SeatConfig } from "@/types/api";

function SeatItem({ seat }: { seat: SeatConfig }) {
  const { seat_id, display_name, model } = seat;
  return (
    <div key={seat_id} className="flex items-center gap-2.5">
      <div className="w-7 h-7 rounded-full bg-indigo-100 flex items-center justify-center flex-shrink-0">
        <span className="text-xs font-bold text-indigo-600">
          {display_name.charAt(0).toUpperCase()}
        </span>
      </div>
      <div className="min-w-0">
        <p className="text-xs font-medium text-gray-700 leading-tight">{display_name}</p>
        <p className="text-xs text-gray-500 truncate">{model}</p>
      </div>
    </div>
  );
}

function PanelCard({
  panel,
  selected,
  onClick,
}: {
  panel: Panel;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`text-left w-full border rounded-xl p-4 transition ${
        selected
          ? "border-indigo-500 bg-indigo-50 ring-1 ring-indigo-500"
          : "border-gray-200 bg-white hover:border-gray-300"
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <h3 className={`text-sm font-medium leading-snug ${selected ? "text-indigo-700" : "text-gray-900"}`}>
          {panel.name}
        </h3>
        {panel.is_system && (
          <span className="flex-shrink-0 text-xs bg-indigo-50 text-indigo-600 px-1.5 py-0.5 rounded">
            System
          </span>
        )}
      </div>
      <p className="text-xs text-gray-500 line-clamp-2 leading-relaxed mb-3">
        {panel.description}
      </p>
      <div className="flex items-center gap-3 text-xs text-gray-500">
        <span>{panel.seats.length} seats</span>
        {panel.use_cases.length > 0 && (
          <span className="truncate text-gray-400">{panel.use_cases[0]}</span>
        )}
      </div>
    </button>
  );
}

function PanelDetail({ panel }: { panel: Panel }) {
  const modModel = panel.moderator_config.model;
  return (
    <div className="bg-gray-50 border border-gray-200 rounded-xl p-5 sticky top-24">
      <div className="flex items-start justify-between mb-3">
        <h2 className="text-base font-semibold text-gray-900">{panel.name}</h2>
        {panel.is_system && (
          <span className="text-xs bg-indigo-50 text-indigo-600 px-1.5 py-0.5 rounded">
            System
          </span>
        )}
      </div>
      <p className="text-sm text-gray-500 mb-4 leading-relaxed">{panel.description}</p>

      {panel.use_cases.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
            Use Cases
          </p>
          <div className="flex flex-wrap gap-1.5">
            {panel.use_cases.map((uc, i) => (
              <span
                key={i}
                className="text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded-full"
              >
                {uc}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="mb-4">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
          Participants ({panel.seats.length})
        </p>
        <div className="space-y-2">
          {panel.seats.map((seat) => (
            <SeatItem key={seat.seat_id} seat={seat} />
          ))}
        </div>
      </div>

      <div>
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
          Moderator
        </p>
        <p className="text-xs text-gray-600">Moderator AI</p>
        <p className="text-xs text-gray-500">{modModel}</p>
      </div>
    </div>
  );
}

export default function PanelSelectionPage() {
  const navigate = useNavigate();
  const { topic, selectedPanel, setSelectedPanel, setCurrentStep } = useNewSessionStore();
  const [previewPanel, setPreviewPanel] = useState<Panel | null>(selectedPanel);

  const { data: panels, isLoading } = usePanels();

  // Redirect if no topic
  if (!topic) {
    void navigate({ to: "/sessions/new/topic" });
    return null;
  }

  const handleSelect = (panel: Panel) => {
    setPreviewPanel(panel);
    setSelectedPanel(panel);
  };

  const handleNext = () => {
    if (!selectedPanel && previewPanel) {
      setSelectedPanel(previewPanel);
    }
    setCurrentStep(3);
    void navigate({ to: "/sessions/new/rules" });
  };

  const canProceed = !!previewPanel;

  return (
    <div className="min-h-screen bg-white">
      <AppNavbar />
      {/* Sub-header */}
      <header className="border-b border-gray-200 bg-white sticky top-[68px] z-10">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-4">
          <Link to="/sessions/new/topic" className="text-gray-400 hover:text-gray-600 transition">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div className="flex-1">
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <span className="text-gray-400">1. Topic</span>
              <span>/</span>
              <span className="text-indigo-600 font-medium">2. Panel</span>
              <span>/</span>
              <span>3. Rules</span>
            </div>
          </div>
          <button
            onClick={handleNext}
            disabled={!canProceed}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition"
          >
            Next: Rules →
          </button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-10">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Choose a Panel</h1>
          <p className="text-gray-500 text-sm mt-1">
            Select the AI panel configuration that best fits your discussion
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Panel Grid */}
          <div className="lg:col-span-2">
            {isLoading ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="bg-white border border-gray-200 rounded-xl p-4 animate-pulse">
                    <div className="h-4 bg-gray-200 rounded mb-2 w-2/3" />
                    <div className="h-3 bg-gray-200 rounded mb-1 w-full" />
                    <div className="h-3 bg-gray-200 rounded w-4/5" />
                  </div>
                ))}
              </div>
            ) : panels?.length === 0 ? (
              <div className="text-center py-12 border border-dashed border-gray-300 rounded-xl">
                <p className="text-gray-500 text-sm">No panels available</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {panels?.map((panel) => (
                  <PanelCard
                    key={panel.id}
                    panel={panel}
                    selected={previewPanel?.id === panel.id}
                    onClick={() => handleSelect(panel)}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Detail Sidebar */}
          <div>
            {previewPanel ? (
              <PanelDetail panel={previewPanel} />
            ) : (
              <div className="bg-white border border-dashed border-gray-300 rounded-xl p-5 text-center">
                <p className="text-xs text-gray-500">
                  Click a panel to preview its configuration
                </p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
