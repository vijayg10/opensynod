import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiJson, apiFetch } from "@/lib/api";
import type {
  Session,
  CreateSessionRequest,
  EstimateRequest,
  EstimateResponse,
  ApiMessage,
  ApiSource,
  SessionOutcome,
  AuditEvent,
  OrgSession,
  InterventionRequest,
  VoteRequest,
  Vote,
  DecisionOutcomeRequest,
} from "@/types/api";

export const sessionKeys = {
  all: ["sessions"] as const,
  orgList: (params?: Record<string, string>) => ["sessions", "org", params] as const,
  detail: (id: string) => ["sessions", id] as const,
  messages: (id: string, params?: Record<string, string>) =>
    ["sessions", id, "messages", params] as const,
  sources: (id: string) => ["sessions", id, "sources"] as const,
  outcome: (id: string) => ["sessions", id, "outcome"] as const,
  audit: (id: string) => ["sessions", id, "audit"] as const,
  votes: (id: string) => ["sessions", id, "votes"] as const,
};

// Org session listing
export function useOrgSessions(params?: {
  q?: string;
  status?: string;
  panel_id?: string;
  from?: string;
  to?: string;
}) {
  const query = new URLSearchParams();
  if (params?.q) query.set("q", params.q);
  if (params?.status) query.set("status", params.status);
  if (params?.panel_id) query.set("panel_id", params.panel_id);
  if (params?.from) query.set("from", params.from);
  if (params?.to) query.set("to", params.to);
  const queryStr = query.toString();

  return useQuery({
    queryKey: sessionKeys.orgList(params as Record<string, string>),
    queryFn: () =>
      apiJson<OrgSession[]>(
        `/api/v1/org/sessions${queryStr ? `?${queryStr}` : ""}`
      ),
  });
}

// Individual session
export function useSession(id: string) {
  return useQuery({
    queryKey: sessionKeys.detail(id),
    queryFn: () => apiJson<Session>(`/api/v1/sessions/${id}`),
    enabled: !!id,
  });
}

// Session messages
export function useSessionMessages(
  sessionId: string,
  params?: {
    seat_id?: string;
    phase?: string;
    limit?: number;
    offset?: number;
  }
) {
  const query = new URLSearchParams();
  if (params?.seat_id) query.set("seat_id", params.seat_id);
  if (params?.phase) query.set("phase", params.phase);
  if (params?.limit !== undefined) query.set("limit", String(params.limit));
  if (params?.offset !== undefined) query.set("offset", String(params.offset));
  const queryStr = query.toString();

  return useQuery({
    queryKey: sessionKeys.messages(sessionId, params as Record<string, string>),
    queryFn: () =>
      apiJson<ApiMessage[]>(
        `/api/v1/sessions/${sessionId}/messages${queryStr ? `?${queryStr}` : ""}`
      ),
    enabled: !!sessionId,
  });
}

// Session sources
export function useSessionSources(sessionId: string) {
  return useQuery({
    queryKey: sessionKeys.sources(sessionId),
    queryFn: () => apiJson<ApiSource[]>(`/api/v1/sessions/${sessionId}/sources`),
    enabled: !!sessionId,
  });
}

// Session outcome
export function useSessionOutcome(sessionId: string) {
  return useQuery({
    queryKey: sessionKeys.outcome(sessionId),
    queryFn: () => apiJson<SessionOutcome>(`/api/v1/sessions/${sessionId}/outcome`),
    enabled: !!sessionId,
  });
}

// Session audit
export function useSessionAudit(sessionId: string) {
  return useQuery({
    queryKey: sessionKeys.audit(sessionId),
    queryFn: () => apiJson<AuditEvent[]>(`/api/v1/sessions/${sessionId}/audit`),
    enabled: !!sessionId,
  });
}

// Create session
export function useCreateSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateSessionRequest) =>
      apiJson<Session>("/api/v1/sessions", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: sessionKeys.all });
    },
  });
}

// Estimate session cost
export function useEstimateSession() {
  return useMutation({
    mutationFn: (data: EstimateRequest) =>
      apiJson<EstimateResponse>("/api/v1/sessions/estimate", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  });
}

// Session control mutations
export function useStartSession(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiJson<Session>(`/api/v1/sessions/${sessionId}/start`, {
        method: "POST",
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: sessionKeys.detail(sessionId),
      });
    },
  });
}

export function usePauseSession(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiJson<Session>(`/api/v1/sessions/${sessionId}/pause`, {
        method: "POST",
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: sessionKeys.detail(sessionId),
      });
    },
  });
}

export function useResumeSession(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiJson<Session>(`/api/v1/sessions/${sessionId}/resume`, {
        method: "POST",
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: sessionKeys.detail(sessionId),
      });
    },
  });
}

export function useEndSession(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiJson<Session>(`/api/v1/sessions/${sessionId}/end`, {
        method: "POST",
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: sessionKeys.detail(sessionId),
      });
    },
  });
}

export function useSkipTurn(sessionId: string) {
  return useMutation({
    mutationFn: () =>
      apiJson(`/api/v1/sessions/${sessionId}/skip-turn`, { method: "POST" }),
  });
}

export function useIntervene(sessionId: string) {
  return useMutation({
    mutationFn: (data: InterventionRequest) =>
      apiJson<ApiMessage>(`/api/v1/sessions/${sessionId}/interventions`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
  });
}

export function useSessionVotes(sessionId: string) {
  return useQuery({
    queryKey: sessionKeys.votes(sessionId),
    queryFn: () => apiJson<Vote[]>(`/api/v1/sessions/${sessionId}/votes`),
    enabled: !!sessionId,
    refetchInterval: 5000, // Poll during voting phase
  });
}

export function useVote(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: VoteRequest) =>
      apiJson<Vote>(`/api/v1/sessions/${sessionId}/votes`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: sessionKeys.votes(sessionId) });
      void queryClient.invalidateQueries({ queryKey: sessionKeys.detail(sessionId) });
    },
  });
}

export function useMarkDecisionOutcome(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: DecisionOutcomeRequest) =>
      apiJson<{ decision_outcome_id: string }>(
        `/api/v1/sessions/${sessionId}/decision-outcome`,
        { method: "POST", body: JSON.stringify(data) }
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: sessionKeys.detail(sessionId) });
    },
  });
}

export function useExportSession(sessionId: string) {
  return {
    download: async (format: "json" | "markdown" | "pdf") => {
      const res = await apiFetch(
        `/api/v1/sessions/${sessionId}/export?format=${format}`
      );
      if (!res.ok) throw new Error("Export failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `session-${sessionId}.${format === "markdown" ? "md" : format}`;
      a.click();
      URL.revokeObjectURL(url);
    },
  };
}
