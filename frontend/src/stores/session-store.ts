import { create } from "zustand";
import type { VoteChoice, SessionStatus } from "@/types/api";

export interface Message {
  id: string;
  sessionId: string;
  seatId: string | null;
  authorType: "agent" | "human" | "moderator" | "system";
  content: string;
  model: string | null;
  phase: string | null;
  createdAt: string;
  streaming?: boolean;
}

export interface Participant {
  userId: string;
  name: string;
  avatarUrl?: string;
  online: boolean;
}

export interface Source {
  id: string;
  url: string;
  title: string;
  domain: string;
  retrievedAt: string;
  seatId: string | null;
}

export interface LiveVote {
  voterId: string;
  voterType: "agent" | "human";
  voterName?: string;
  seatId?: string | null;
  vote: VoteChoice;
  rationale?: string;
}

interface SessionStore {
  sessionId: string | null;
  sessionStatus: SessionStatus | null;
  messages: Message[];
  currentPhase: string | null;
  currentSpeaker: string | null;
  participants: Participant[];
  sources: Source[];
  costActual: number;
  costLimit: number | null;
  themes: string[];
  liveVotes: LiveVote[];

  setSessionId: (id: string) => void;
  setSessionStatus: (status: SessionStatus) => void;
  appendMessage: (msg: Message) => void;
  appendToken: (messageId: string, token: string) => void;
  finalizeMessage: (messageId: string) => void;
  setPhase: (phase: string) => void;
  setCurrentSpeaker: (seatId: string | null) => void;
  addSource: (source: Source) => void;
  updateCost: (actual: number, limit: number | null) => void;
  setThemes: (themes: string[]) => void;
  addLiveVote: (vote: LiveVote) => void;
  reset: () => void;
}

const initialState = {
  sessionId: null,
  sessionStatus: null,
  messages: [],
  currentPhase: null,
  currentSpeaker: null,
  participants: [],
  sources: [],
  costActual: 0,
  costLimit: null,
  themes: [],
  liveVotes: [],
};

export const useSessionStore = create<SessionStore>((set) => ({
  ...initialState,

  setSessionId: (id) => set({ sessionId: id }),

  setSessionStatus: (status) => set({ sessionStatus: status }),

  appendMessage: (msg) =>
    set((state) => ({ messages: [...state.messages, msg] })),

  appendToken: (messageId, token) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === messageId ? { ...m, content: m.content + token } : m
      ),
    })),

  finalizeMessage: (messageId) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === messageId ? { ...m, streaming: false } : m
      ),
    })),

  setPhase: (phase) => set({ currentPhase: phase }),

  setCurrentSpeaker: (seatId) => set({ currentSpeaker: seatId }),

  addSource: (source) =>
    set((state) => ({ sources: [...state.sources, source] })),

  updateCost: (actual, limit) => set({ costActual: actual, costLimit: limit }),

  setThemes: (themes) => set({ themes }),

  addLiveVote: (vote) =>
    set((state) => ({
      liveVotes: [
        // Replace if same voter already voted
        ...state.liveVotes.filter((v) => v.voterId !== vote.voterId),
        vote,
      ],
    })),

  reset: () => set(initialState),
}));
