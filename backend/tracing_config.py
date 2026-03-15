import os
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

def configure_tracing(app=None, service_name: str = "alluci-sovereign-agent"):
    """
    Initializes OpenTelemetry Tracing for distributed request tracking.
    
    In production: Exports spans to an OTLP-compatible collector (Jaeger, Honeycomb, Datadog).
    In development: Emits spans to console for verification.
    """
    resource = Resource.create({
        "service.name": service_name,
        "deployment.environment": os.getenv("APP_ENV", "development"),
        "version": "2.1.0"
    })
    
    provider = TracerProvider(resource=resource)
    
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        # Production: OTLP over gRPC or HTTP
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
    else:
        # Development: Simple console output
        processor = BatchSpanProcessor(ConsoleSpanExporter())
        provider.add_span_processor(processor)
        
    trace.set_tracer_provider(provider)
    
    if app:
        # Auto-instrument FastAPI routes and HTTPX requests
        FastAPIInstrumentor.instrument_app(app)
        HTTPXClientInstrumentor().instrument()

def get_tracer(name: str):
    """Utility to obtain a tracer instance for manual span creation."""
    return trace.get_tracer(name)
