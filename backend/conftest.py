# conftest.py – Robust stubs for optional external SDKs, ensuring import‑safe test collection.
# The Alluci Sovereign Agent is local‑first; external provider APIs are optional.
# This file provides minimal placeholder implementations for the SDKs that may be absent.
# It ensures that imports succeed and that any attempt to use an unavailable client
# raises a clear RuntimeError, which the test suite can treat as a "service not configured"
# situation.

import sys
import types
import importlib.machinery

def _dummy_spec(name: str):
    """Return a dummy ModuleSpec for a fake module."""
    return importlib.machinery.ModuleSpec(name, None)

# ----- OpenAI stub -------------------------------------------------------
openai_mod = types.ModuleType('openai')
openai_mod.__spec__ = _dummy_spec('openai')

class _OpenAIChatCompletions:
    @staticmethod
    async def create(*args, **kwargs):
        raise RuntimeError("OpenAI completions not available in test environment")

class _OpenAIChat:
    completions = _OpenAIChatCompletions()

class AsyncOpenAI:
    def __init__(self, *args, **kwargs):
        self.chat = _OpenAIChat()

setattr(openai_mod, 'AsyncOpenAI', AsyncOpenAI)
sys.modules['openai'] = openai_mod

# ----- Cohere stub -------------------------------------------------------
cohere_mod = types.ModuleType('cohere')
cohere_mod.__spec__ = _dummy_spec('cohere')

class AsyncCohereClient:
    def __init__(self, *args, **kwargs):
        pass

    async def chat(self, *args, **kwargs):
        raise RuntimeError("Cohere client not configured in test environment")

setattr(cohere_mod, 'AsyncClient', AsyncCohereClient)
sys.modules['cohere'] = cohere_mod

# ----- Anthropic stub ----------------------------------------------------
anthropic_mod = types.ModuleType('anthropic')
anthropic_mod.__spec__ = _dummy_spec('anthropic')

class _AnthropicMessages:
    @staticmethod
    async def create(*args, **kwargs):
        raise RuntimeError("Anthropic messages not available in test environment")

class AsyncAnthropic:
    def __init__(self, *args, **kwargs):
        self.messages = _AnthropicMessages()

setattr(anthropic_mod, 'AsyncAnthropic', AsyncAnthropic)
sys.modules['anthropic'] = anthropic_mod
setattr(anthropic_mod, 'AsyncAnthropic', AsyncAnthropic)

# ----- Gemini (Google Gen AI SDK) stub -----------------------------------
google_mod = types.ModuleType('google')
google_mod.__spec__ = _dummy_spec('google')

genai_mod = types.ModuleType('google.genai')
genai_mod.__spec__ = _dummy_spec('google.genai')
genai_types_mod = types.ModuleType('google.genai.types')
genai_types_mod.__spec__ = _dummy_spec('google.genai.types')

class _StubType:
    """Accepts and stores any constructor kwargs, mirroring google.genai.types models."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class GenerateContentConfig(_StubType):
    pass

class HttpOptions(_StubType):
    pass

setattr(genai_types_mod, 'GenerateContentConfig', GenerateContentConfig)
setattr(genai_types_mod, 'HttpOptions', HttpOptions)

class _AioModels:
    async def generate_content(self, *args, **kwargs):
        raise RuntimeError("Gemini model not configured in test environment")

class _Aio:
    def __init__(self):
        self.models = _AioModels()

class Client:
    def __init__(self, *args, **kwargs):
        self.aio = _Aio()

setattr(genai_mod, 'Client', Client)
setattr(genai_mod, 'types', genai_types_mod)
# expose "genai" attribute on google module and register submodules
setattr(google_mod, 'genai', genai_mod)
sys.modules['google'] = google_mod
sys.modules['google.genai'] = genai_mod
sys.modules['google.genai.types'] = genai_types_mod

# ----- Boto3 / AIOboto3 stub -------------------------------------------
aioboto3_mod = types.ModuleType('aioboto3')
aioboto3_mod.__spec__ = _dummy_spec('aioboto3')
sys.modules['aioboto3'] = aioboto3_mod

boto3_mod = types.ModuleType('boto3')
    
boto3_mod.__spec__ = _dummy_spec('boto3')
sys.modules['boto3'] = boto3_mod

# Ensure that any deeper submodule imports (e.g., google.api_core) resolve to a placeholder.
for parent in list(sys.modules.keys()):
    if '.' in parent:
        root = parent.split('.')[0]
        if root not in sys.modules:
            placeholder = types.ModuleType(root)
            placeholder.__spec__ = _dummy_spec(root)
            sys.modules[root] = placeholder

# No further test configuration needed; the presence of these placeholders prevents import errors.
