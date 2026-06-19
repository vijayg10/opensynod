"""OpenTelemetry tracing configuration."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def configure_tracing(service_name: str = "opensynod-api") -> None:
    """Configure OpenTelemetry tracing with OTLP export.

    Gracefully skips if the opentelemetry SDK is not installed.
    Set OTEL_EXPORTER_OTLP_ENDPOINT env var to enable export.
    """
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME

        resource = Resource.create({SERVICE_NAME: service_name})
        provider = TracerProvider(resource=resource)

        # Try OTLP exporter
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            import os

            endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
            if endpoint:
                exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
                provider.add_span_processor(BatchSpanProcessor(exporter))
                logger.info("OpenTelemetry OTLP tracing configured → %s", endpoint)
        except ImportError:
            # opentelemetry-exporter-otlp-proto-grpc not installed
            pass

        trace.set_tracer_provider(provider)

        # Auto-instrument FastAPI
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
            FastAPIInstrumentor().instrument()
        except ImportError:
            pass

        # Auto-instrument SQLAlchemy
        try:
            from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
            SQLAlchemyInstrumentor().instrument()
        except ImportError:
            pass

        # Auto-instrument httpx
        try:
            from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
            HTTPXClientInstrumentor().instrument()
        except ImportError:
            pass

    except ImportError:
        logger.debug("opentelemetry-sdk not installed; tracing disabled")


def get_tracer(name: str = "opensynod") -> "trace.Tracer":  # type: ignore[name-defined]
    """Return a tracer for manual span creation."""
    try:
        from opentelemetry import trace
        return trace.get_tracer(name)
    except ImportError:
        # Return a no-op stub
        class _NoOpTracer:
            def start_as_current_span(self, *_a: object, **_kw: object):  # type: ignore[override]
                from contextlib import contextmanager

                @contextmanager
                def _noop():  # type: ignore[return]
                    yield None

                return _noop()

        return _NoOpTracer()  # type: ignore[return-value]
