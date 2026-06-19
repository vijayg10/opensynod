// API Types for OpenSynod

// Auth
export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export interface RefreshResponse {
  access_token: string;
}

// User
export interface User {
  id: string;
  email: string;
  display_name: string;
  avatar_url?: string;
  created_at: string;
}

// Panels — types match backend app/panels/schemas.py
export interface SeatPersona {
  role: string;
  domain_focus: string[];
  disposition: string;
  expertise_level: string;
  system_prompt_overlay: string;
}

export interface SeatDiscussionRules {
  must_cite_sources?: boolean;
  hidden_commitment_required?: boolean;
  min_challenges_per_session?: number;
}

export interface SeatConfig {
  seat_id: string;
  display_name: string;
  color: string;
  avatar: string;
  model: string;
  persona: SeatPersona;
  discussion_rules?: SeatDiscussionRules;
}

export interface ModeratorConfig {
  model: string;
  system_prompt: string;
  auto_summary_every_n_turns: number;
  convergence_speed_threshold: number;
}

export interface PanelDiscussionRules {
  hidden_position_protocol?: boolean;
  min_turns_before_convergence?: number;
  max_turns?: number;
  allowed_tools?: string[];
  adversarial_framing?: boolean;
}

// Session-level discussion rules (user-configured in wizard)
export interface DiscussionRules {
  max_turns_per_phase?: number;
  opening_statement_words?: number;
  rebuttal_words?: number;
  allow_human_interventions?: boolean;
  require_citations?: boolean;
  anonymize_agents?: boolean;
  speaking_order?: "round_robin" | "dynamic" | "moderator_assigned";
  phases?: string[];
  custom_rules?: string[];
}

export interface Panel {
  id: string;
  name: string;
  description: string;
  use_cases: string[];
  seats: SeatConfig[];
  moderator_config: ModeratorConfig;
  discussion_rules: PanelDiscussionRules;
  is_system: boolean;
}

// Sessions
export type SessionStatus =
  | "draft"
  | "queued"
  | "running"
  | "paused"
  | "voting"
  | "concluded"
  | "failed";

export type SessionPhase =
  | "opening"
  | "exploration"
  | "debate"
  | "convergence"
  | "vote";

export type OutcomeType = "recommendation" | "exploration" | "risk_assessment";

export interface Session {
  id: string;
  topic: string;
  outcome_type: OutcomeType;
  success_criteria?: string;
  panel_id: string | null;
  panel_snapshot_json: Panel;
  discussion_rules_json: DiscussionRules;
  status: SessionStatus;
  phase: SessionPhase | null;
  cost_estimate?: number;
  cost_limit?: number;
  cost_actual: number;
  started_at?: string;
  concluded_at?: string;
  created_at: string;
  error?: string;
}

export interface CreateSessionRequest {
  topic: string;
  outcome_type: OutcomeType;
  success_criteria?: string;
  panel_id: string;
  discussion_rules?: Partial<DiscussionRules>;
  cost_limit?: number;
}

export interface EstimateRequest {
  panel_id: string;
  duration_turns?: number;
}

export interface EstimateResponse {
  cost_low: number;
  cost_high: number;
  duration_min: number;
  turns: number;
}

// Messages
export interface ApiMessage {
  id: string;
  session_id: string;
  seat_id: string | null;
  author_type: "agent" | "human" | "moderator" | "system";
  content: string;
  model: string | null;
  phase_at_creation: string | null;
  created_at: string;
}

// Messages come back as a plain list from the backend
export type MessagesResponse = ApiMessage[];

// Sources
export interface ApiSource {
  id: string;
  session_id: string;
  url: string;
  title: string;
  domain: string;
  retrieved_at: string;
  retrieval_seat_id: string | null;
}

// Outcome
export interface SessionOutcome {
  id: string;
  session_id: string;
  type: "recommendation" | "no_consensus";
  statement: string;
  supporting_arguments: string[];
  substantive_dissents: string[];
  divergence_noted: boolean;
  confidence_score: number;
  source_density_score: number;
  created_at: string;
}

// Votes
export type VoteChoice = "yes" | "no" | "abstain";

export interface Vote {
  id: string;
  session_id: string;
  voter_id: string;
  voter_type: "agent" | "human";
  seat_id?: string | null;
  vote: VoteChoice;
  rationale: string;
  submitted_at: string;
}

export interface VoteRequest {
  vote: VoteChoice;
  rationale?: string;
}

// Interventions
export interface InterventionRequest {
  content: string;
  seat_id?: string;
}

// Org
export interface OrgSession {
  id: string;
  topic: string;
  status: SessionStatus;
  phase: SessionPhase | null;
  panel_id: string;
  panel_name?: string;
  cost_actual: number;
  created_at: string;
  concluded_at?: string;
  created_by: string;
}

// Org sessions come back as a plain list from the backend
export type OrgSessionsResponse = OrgSession[];

export interface OrgMember {
  id: string;
  user_id: string;
  email: string;
  display_name: string;
  role: "admin" | "member" | "viewer";
  joined_at: string;
}

// Audit
export interface AuditEvent {
  id: string;
  session_id: string;
  actor_id: string;
  actor_type: string;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
}

// SSE Event payloads
export interface SSETokenEvent {
  message_id: string;
  session_id: string;
  token: string;
}

export interface SSEMessageEvent {
  message_id: string;
  session_id: string;
  seat_id: string | null;
  author_type: "agent" | "human" | "moderator" | "system";
  content: string;
  phase: string | null;
}

export interface SSEPhaseEvent {
  session_id: string;
  phase: SessionPhase;
  previous_phase: SessionPhase | null;
}

export interface SSESpeakerEvent {
  session_id: string;
  seat_id: string | null;
}

export interface SSECostEvent {
  session_id: string;
  cost_actual: number;
  cost_limit: number | null;
}

export interface SSEThemeEvent {
  session_id: string;
  themes: string[];
}

export interface SSESourceEvent {
  session_id: string;
  source: ApiSource;
}

export interface SSEStatusEvent {
  session_id: string;
  status: SessionStatus;
}

export interface SSEVoteUpdateEvent {
  voter_type: "agent" | "human";
  voter_id: string;
  voter_name?: string;
  seat_id?: string | null;
  vote: VoteChoice;
  rationale?: string;
  running_tally?: {
    yes: number;
    no: number;
    abstain: number;
  };
}

export interface DecisionOutcomeRequest {
  result: "adopted_success" | "adopted_failure" | "chose_differently";
  notes?: string;
}
