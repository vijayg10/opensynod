import { create } from "zustand";
import type { OutcomeType, Panel, DiscussionRules } from "@/types/api";

interface NewSessionState {
  // Step 1: Topic
  topic: string;
  outcomeType: OutcomeType;
  successCriteria: string;

  // Step 2: Panel
  selectedPanelId: string | null;
  selectedPanel: Panel | null;

  // Step 3: Rules
  discussionRules: Partial<DiscussionRules>;

  // Wizard step tracking
  currentStep: 1 | 2 | 3;

  // Actions
  setTopic: (topic: string) => void;
  setOutcomeType: (type: OutcomeType) => void;
  setSuccessCriteria: (criteria: string) => void;
  setSelectedPanel: (panel: Panel) => void;
  setDiscussionRules: (rules: Partial<DiscussionRules>) => void;
  setCurrentStep: (step: 1 | 2 | 3) => void;
  reset: () => void;
}

const defaultRules: Partial<DiscussionRules> = {
  allow_human_interventions: true,
  require_citations: false,
  speaking_order: "round_robin",
};

const initialState = {
  topic: "",
  outcomeType: "recommendation" as OutcomeType,
  successCriteria: "",
  selectedPanelId: null,
  selectedPanel: null,
  discussionRules: defaultRules,
  currentStep: 1 as const,
};

export const useNewSessionStore = create<NewSessionState>((set) => ({
  ...initialState,

  setTopic: (topic) => set({ topic }),

  setOutcomeType: (outcomeType) => set({ outcomeType }),

  setSuccessCriteria: (successCriteria) => set({ successCriteria }),

  setSelectedPanel: (panel) =>
    set({ selectedPanelId: panel.id, selectedPanel: panel }),

  setDiscussionRules: (rules) =>
    set((state) => ({
      discussionRules: { ...state.discussionRules, ...rules },
    })),

  setCurrentStep: (currentStep) => set({ currentStep }),

  reset: () => set({ ...initialState }),
}));
