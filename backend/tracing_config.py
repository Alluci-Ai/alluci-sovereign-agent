import os
try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
except ImportError:
    class _DummySpan:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def set_attribute(self, *args, **kwargs): pass
        def add_event(self, *args, **kwargs): pass
        def set_status(self, *args, **kwargs): pass
        def record_exception(self, *args, **kwargs): pass

    class _DummyTracer:
        def start_as_current_span(self, *args, **kwargs):
            return _DummySpan()

    class _Dummy:
        def __getattr__(self, name):
            if name == "get_tracer":
                return lambda *args, **kwargs: _DummyTracer()
            return lambda *args, **kwargs: None
        def __call__(self, *args, **kwargs):
            return self
    
    trace = _Dummy()
    Resource = _Dummy()
    class _TracerProvider(_Dummy):
        def __init__(self, *args, **kwargs): pass
        def add_span_processor(self, *args, **kwargs): pass

    TracerProvider = _TracerProvider

    class BatchSpanProcessor(_Dummy):
        def __init__(self, *args, **kwargs): pass

    class ConsoleSpanExporter(_Dummy):
        def __init__(self, *args, **kwargs): pass

    class OTLPSpanExporter(_Dummy):
        def __init__(self, *args, **kwargs): pass

    class FastAPIInstrumentor(_Dummy):
        @classmethod
        def instrument_app(cls, *args, **kwargs): pass

    class HTTPXClientInstrumentor(_Dummy):
        def instrument(self, *args, **kwargs): pass

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
        processor = BatchSpanProcessor(exporter)  # type: ignore
        provider.add_span_processor(processor)    # type: ignore
    else:
        # Development: Simple console output
        processor = BatchSpanProcessor(ConsoleSpanExporter())  # type: ignore
        provider.add_span_processor(processor)    # type: ignore
        
    trace.set_tracer_provider(provider)  # type: ignore
    
    if app:
        # Auto-instrument FastAPI routes and HTTPX requests
        FastAPIInstrumentor.instrument_app(app)
        HTTPXClientInstrumentor().instrument()

def get_tracer(name: str):
    """Utility to obtain a tracer instance for manual span creation."""
    return trace.get_tracer(name)
