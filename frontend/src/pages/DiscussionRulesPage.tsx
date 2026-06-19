import { useNavigate, Link } from "@tanstack/react-router";
import { useForm, Controller } from "react-hook-form";
import { useNewSessionStore } from "@/stores/new-session-store";
import { useCreateSession } from "@/hooks/useSessions";
import AppNavbar from "@/components/AppNavbar";
import type { DiscussionRules } from "@/types/api";

type RulesFormValues = {
  allow_human_interventions: boolean;
  require_citations: boolean;
  anonymize_agents: boolean;
  speaking_order: "round_robin" | "dynamic" | "moderator_assigned";
  max_turns_per_phase: number;
  opening_statement_words: number;
  rebuttal_words: number;
};

const SPEAKING_ORDER_OPTIONS: {
  value: DiscussionRules["speaking_order"];
  label: string;
  description: string;
}[] = [
  {
    value: "round_robin",
    label: "Round Robin",
    description: "Each participant speaks in a fixed rotation",
  },
  {
    value: "dynamic",
    label: "Dynamic",
    description: "Participants respond based on relevance",
  },
  {
    value: "moderator_assigned",
    label: "Moderator Assigned",
    description: "Moderator decides who speaks next",
  },
];

export default function DiscussionRulesPage() {
  const navigate = useNavigate();
  const { topic, selectedPanel, selectedPanelId, outcomeType, successCriteria, discussionRules, setDiscussionRules } =
    useNewSessionStore();

  const createSession = useCreateSession();

  const { register, handleSubmit, control, watch } = useForm<RulesFormValues>({
    defaultValues: {
      allow_human_interventions: discussionRules.allow_human_interventions ?? true,
      require_citations: discussionRules.require_citations ?? false,
      anonymize_agents: discussionRules.anonymize_agents ?? false,
      speaking_order: discussionRules.speaking_order ?? "round_robin",
      max_turns_per_phase: discussionRules.max_turns_per_phase ?? 4,
      opening_statement_words: discussionRules.opening_statement_words ?? 200,
      rebuttal_words: discussionRules.rebuttal_words ?? 150,
    },
  });

  // Redirect if wizard incomplete
  if (!topic || !selectedPanelId) {
    void navigate({ to: "/sessions/new/topic" });
    return null;
  }

  const watchedOrder = watch("speaking_order");

  const onSubmit = async (data: RulesFormValues) => {
    const rules: Partial<DiscussionRules> = {
      allow_human_interventions: data.allow_human_interventions,
      require_citations: data.require_citations,
      anonymize_agents: data.anonymize_agents,
      speaking_order: data.speaking_order,
      max_turns_per_phase: data.max_turns_per_phase,
      opening_statement_words: data.opening_statement_words,
      rebuttal_words: data.rebuttal_words,
    };
    setDiscussionRules(rules);

    const session = await createSession.mutateAsync({
      topic,
      outcome_type: outcomeType,
      success_criteria: successCriteria || undefined,
      panel_id: selectedPanelId,
      discussion_rules: rules,
    });

    void navigate({ to: "/sessions/$sessionId", params: { sessionId: session.id } });
  };

  return (
    <div className="min-h-screen bg-white">
      <AppNavbar />
      {/* Sub-header */}
      <header className="border-b border-gray-200 bg-white sticky top-[68px] z-10">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center gap-4">
          <Link to="/sessions/new/panel" className="text-gray-500 hover:text-gray-700 transition">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div className="flex-1">
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <span className="text-gray-500">1. Topic</span>
              <span>/</span>
              <span className="text-gray-500">2. Panel</span>
              <span>/</span>
              <span className="text-indigo-600 font-medium">3. Rules</span>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-10">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">Discussion Rules</h1>
          <p className="text-gray-500 text-sm mt-1">
            Configure how the discussion will be conducted
          </p>
        </div>

        {/* Summary */}
        <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 mb-8">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-gray-500 text-xs mb-0.5">Topic</p>
              <p className="text-gray-700 line-clamp-2 text-sm">{topic}</p>
            </div>
            <div>
              <p className="text-gray-500 text-xs mb-0.5">Outcome</p>
              <p className="text-gray-700 capitalize">{outcomeType}</p>
            </div>
            <div>
              <p className="text-gray-500 text-xs mb-0.5">Panel</p>
              <p className="text-gray-700">{selectedPanel?.name ?? selectedPanelId}</p>
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-8">
          {/* Speaking Order */}
          <div>
            <h2 className="text-sm font-medium text-gray-700 mb-3">Speaking Order</h2>
            <Controller
              name="speaking_order"
              control={control}
              render={({ field }) => (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {SPEAKING_ORDER_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => field.onChange(opt.value)}
                      className={`text-left p-3.5 rounded-lg border transition ${
                        field.value === opt.value
                          ? "border-indigo-500 bg-indigo-50"
                          : "border-gray-200 bg-white hover:border-gray-300"
                      }`}
                    >
                      <p className={`text-sm font-medium mb-0.5 ${field.value === opt.value ? "text-indigo-700" : "text-gray-700"}`}>
                        {opt.label}
                      </p>
                      <p className="text-xs text-gray-500">{opt.description}</p>
                    </button>
                  ))}
                </div>
              )}
            />
            {watchedOrder && (
              <p className="mt-2 text-xs text-gray-400">
                Selected: <span className="text-gray-500">{watchedOrder.replace("_", " ")}</span>
              </p>
            )}
          </div>

          {/* Toggles */}
          <div>
            <h2 className="text-sm font-medium text-gray-700 mb-3">Behaviour</h2>
            <div className="bg-white border border-gray-200 rounded-xl divide-y divide-gray-200">
              {(
                [
                  {
                    name: "allow_human_interventions" as const,
                    label: "Allow Human Interventions",
                    description: "You can send messages during the discussion",
                  },
                  {
                    name: "require_citations" as const,
                    label: "Require Citations",
                    description: "Agents must cite sources for factual claims",
                  },
                  {
                    name: "anonymize_agents" as const,
                    label: "Anonymize Agents",
                    description: "Hide agent names and models during discussion",
                  },
                ] as const
              ).map((toggle) => (
                <label
                  key={toggle.name}
                  className="flex items-center justify-between px-4 py-3.5 cursor-pointer hover:bg-gray-50 transition"
                >
                  <div>
                    <p className="text-sm text-gray-700">{toggle.label}</p>
                    <p className="text-xs text-gray-500">{toggle.description}</p>
                  </div>
                  <div className="relative ml-4 flex-shrink-0">
                    <input
                      type="checkbox"
                      className="sr-only peer"
                      {...register(toggle.name)}
                    />
                    <div className="w-10 h-5 bg-gray-300 peer-checked:bg-indigo-600 rounded-full transition after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:bg-white after:rounded-full after:w-4 after:h-4 after:transition-all peer-checked:after:translate-x-5" />
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Numeric Settings */}
          <div>
            <h2 className="text-sm font-medium text-gray-700 mb-3">Limits</h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs text-gray-500 mb-1.5">
                  Max Turns per Phase
                </label>
                <input
                  type="number"
                  min={1}
                  max={20}
                  className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition"
                  {...register("max_turns_per_phase", { valueAsNumber: true })}
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1.5">
                  Opening Statement Words
                </label>
                <input
                  type="number"
                  min={50}
                  max={1000}
                  step={50}
                  className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition"
                  {...register("opening_statement_words", { valueAsNumber: true })}
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1.5">
                  Rebuttal Words
                </label>
                <input
                  type="number"
                  min={50}
                  max={500}
                  step={50}
                  className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition"
                  {...register("rebuttal_words", { valueAsNumber: true })}
                />
              </div>
            </div>
          </div>

          {/* Error */}
          {createSession.error && (
            <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3">
              <p className="text-sm text-red-600">{createSession.error.message}</p>
            </div>
          )}

          {/* Submit */}
          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={createSession.isPending}
              className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-white flex items-center gap-2"
            >
              {createSession.isPending ? (
                <>
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Creating...
                </>
              ) : (
                "Start Discussion"
              )}
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}
