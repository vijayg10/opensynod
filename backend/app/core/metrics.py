"""Custom Prometheus metrics for AI Round Table Conference."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# Discussion metrics
discussion_duration_seconds = Histogram(
    "discussion_duration_seconds",
    "Duration of a complete discussion in seconds",
    ["panel", "outcome_type"],
    buckets=[60, 300, 600, 1200, 1800, 3600, 7200],
)

discussion_turns_total = Counter(
    "discussion_turns_total",
    "Total number of agent turns across all discussions",
    ["panel"],
)

# LLM metrics
llm_request_duration_seconds = Histogram(
    "llm_request_duration_seconds",
    "Duration of LLM API requests in seconds",
    ["provider", "model"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

llm_tokens_total = Counter(
    "llm_tokens_total",
    "Total LLM tokens processed",
    ["provider", "model", "direction"],  # direction: in | out
)

llm_cost_usd_total = Counter(
    "llm_cost_usd_total",
    "Total LLM cost in USD",
    ["provider", "model"],
)

llm_errors_total = Counter(
    "llm_errors_total",
    "Total LLM errors",
    ["provider", "error_type"],
)

# Session state gauge
session_status_total = Gauge(
    "session_status_total",
    "Number of sessions in each status",
    ["status"],
)

# WebSocket
websocket_connections_active = Gauge(
    "websocket_connections_active",
    "Number of currently active WebSocket connections",
)

# Arq queue
arq_queue_depth = Gauge(
    "arq_queue_depth",
    "Current depth of Arq job queues",
    ["queue_name"],
)

# Interventions
intervention_rate = Counter(
    "intervention_rate",
    "Total human interventions submitted",
)

# Source citations
source_citations_total = Counter(
    "source_citations_total",
    "Total source citations retrieved by agents",
    ["tool", "domain_type"],
)

# API latency (supplements prometheus-fastapi-instrumentator)
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path", "status_code"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)
