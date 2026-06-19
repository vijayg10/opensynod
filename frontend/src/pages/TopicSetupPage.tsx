import { useEffect } from "react";
import { useNavigate, Link } from "@tanstack/react-router";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNewSessionStore } from "@/stores/new-session-store";
import { useEstimateSession } from "@/hooks/useSessions";
import AppNavbar from "@/components/AppNavbar";
import type { OutcomeType } from "@/types/api";

const OUTCOME_TYPES: { value: OutcomeType; label: string; description: string }[] = [
  {
    value: "recommendation",
    label: "Recommendation",
    description: "Produce a clear recommended course of action",
  },
  {
    value: "exploration",
    label: "Exploration",
    description: "Deep-dive analysis and exploration of a topic",
  },
  {
    value: "risk_assessment",
    label: "Risk Assessment",
    description: "Assess risks and produce a risk register",
  },
];

const schema = z.object({
  topic: z.string().min(10, "Topic must be at least 10 characters").max(500),
  outcomeType: z.enum(["recommendation", "exploration", "risk_assessment"]),
  successCriteria: z.string().max(500).optional(),
});

type FormValues = z.infer<typeof schema>;

export default function TopicSetupPage() {
  const navigate = useNavigate();
  const { topic, outcomeType, successCriteria, setTopic, setOutcomeType, setSuccessCriteria, setCurrentStep, selectedPanelId } =
    useNewSessionStore();

  const estimateMutation = useEstimateSession();

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      topic,
      outcomeType,
      successCriteria,
    },
  });


  // Debounced cost estimate when a panel is pre-selected
  useEffect(() => {
    if (!selectedPanelId) return;
    const timer = setTimeout(() => {
      estimateMutation.mutate({ panel_id: selectedPanelId });
    }, 800);
    return () => clearTimeout(timer);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPanelId]);

  const onSubmit = (data: FormValues) => {
    setTopic(data.topic);
    setOutcomeType(data.outcomeType);
    setSuccessCriteria(data.successCriteria ?? "");
    setCurrentStep(2);
    void navigate({ to: "/sessions/new/panel" });
  };

  const estimate = estimateMutation.data;

  return (
    <div className="min-h-screen bg-white">
      <AppNavbar />
      {/* Sub-header */}
      <header className="border-b border-gray-200 bg-white sticky top-[68px] z-10">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center gap-4">
          <Link to="/" className="text-gray-400 hover:text-gray-600 transition">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div className="flex-1">
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <span className="text-indigo-600 font-medium">1. Topic</span>
              <span>/</span>
              <span>2. Panel</span>
              <span>/</span>
              <span>3. Rules</span>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-10">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">Set Up Your Discussion</h1>
          <p className="text-gray-500 text-sm mt-1">
            Define the topic and desired outcome for your AI panel
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Form */}
          <form
            onSubmit={handleSubmit(onSubmit)}
            className="lg:col-span-2 space-y-6"
          >
            {/* Topic */}
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-2">
                Discussion Topic
                <span className="text-red-500 ml-1">*</span>
              </label>
              <textarea
                rows={4}
                placeholder="e.g. What are the trade-offs between microservices and monolithic architectures for a startup scaling from 10 to 100 engineers?"
                className="w-full px-3 py-2.5 bg-white border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:ring-offset-white transition resize-none text-sm"
                {...register("topic")}
              />
              {errors.topic && (
                <p className="mt-1 text-xs text-red-400">{errors.topic.message}</p>
              )}
              <p className="mt-1 text-xs text-gray-500">
                Be specific — the more context you provide, the better the discussion
              </p>
            </div>

            {/* Outcome Type */}
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-2">
                Desired Outcome
                <span className="text-red-500 ml-1">*</span>
              </label>
              <Controller
                name="outcomeType"
                control={control}
                render={({ field }) => (
                  <div className="grid grid-cols-2 gap-3">
                    {OUTCOME_TYPES.map((type) => (
                      <button
                        key={type.value}
                        type="button"
                        onClick={() => field.onChange(type.value)}
                        className={`text-left p-3.5 rounded-lg border transition ${
                          field.value === type.value
                            ? "border-indigo-500 bg-indigo-50 text-indigo-700"
                            : "border-gray-200 bg-white text-gray-700 hover:border-gray-300"
                        }`}
                      >
                        <div className="text-sm font-medium mb-0.5">{type.label}</div>
                        <div className="text-xs text-gray-500">{type.description}</div>
                      </button>
                    ))}
                  </div>
                )}
              />
            </div>

            {/* Success Criteria */}
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-2">
                Success Criteria
                <span className="text-gray-400 ml-2 font-normal">(optional)</span>
              </label>
              <textarea
                rows={2}
                placeholder="e.g. A concrete recommendation with at least 3 supporting arguments and 2 considered alternatives"
                className="w-full px-3 py-2.5 bg-white border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:ring-offset-white transition resize-none text-sm"
                {...register("successCriteria")}
              />
              {errors.successCriteria && (
                <p className="mt-1 text-xs text-red-400">{errors.successCriteria.message}</p>
              )}
            </div>

            {/* Next */}
            <div className="flex justify-end pt-2">
              <button
                type="submit"
                className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-white"
              >
                Next: Choose Panel →
              </button>
            </div>
          </form>

          {/* Cost Estimate Sidebar */}
          <aside className="space-y-4">
            <div className="bg-gray-50 border border-gray-200 rounded-xl p-5">
              <h3 className="text-sm font-medium text-gray-600 mb-4">Cost Estimate</h3>

              {!selectedPanelId && (
                <p className="text-xs text-gray-500">
                  Select a panel on the next step to see cost estimates
                </p>
              )}

              {selectedPanelId && estimateMutation.isPending && (
                <div className="space-y-2 animate-pulse">
                  <div className="h-3 bg-gray-200 rounded w-2/3" />
                  <div className="h-3 bg-gray-200 rounded w-1/2" />
                  <div className="h-3 bg-gray-200 rounded w-3/4" />
                </div>
              )}

              {estimate && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-500">Estimated cost</span>
                    <span className="text-gray-900 font-mono">
                      ${estimate.cost_low.toFixed(2)}–${estimate.cost_high.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-500">Duration</span>
                    <span className="text-gray-900">
                      ~{estimate.duration_min} min
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-500">Turns</span>
                    <span className="text-gray-900">{estimate.turns}</span>
                  </div>
                </div>
              )}
            </div>

            <div className="bg-gray-50 border border-gray-200 rounded-xl p-5">
              <h3 className="text-sm font-medium text-gray-600 mb-2">Tips</h3>
              <ul className="space-y-2 text-xs text-gray-500">
                <li className="flex gap-2">
                  <span className="text-indigo-400 flex-shrink-0">•</span>
                  Specific topics yield better discussions
                </li>
                <li className="flex gap-2">
                  <span className="text-indigo-400 flex-shrink-0">•</span>
                  Use &ldquo;Decision&rdquo; when you need a clear yes/no outcome
                </li>
                <li className="flex gap-2">
                  <span className="text-indigo-400 flex-shrink-0">•</span>
                  Success criteria help focus the moderator
                </li>
              </ul>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
