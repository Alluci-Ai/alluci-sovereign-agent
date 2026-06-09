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

# ----- Gemini (Google Generative AI) stub --------------------------------
google_mod = types.ModuleType('google')
google_mod.__spec__ = _dummy_spec('google')

genai_mod = types.ModuleType('google.generativeai')
genai_mod.__spec__ = _dummy_spec('google.generativeai')

class _GenerativeModel:
    def __init__(self, *args, **kwargs):
        pass

    async def generate_content_async(self, *args, **kwargs):
        raise RuntimeError("Gemini model not configured in test environment")

class genai:
    @staticmethod
    def configure(*args, **kwargs):
        pass

    GenerativeModel = _GenerativeModel

# expose "genai" attribute on google module and register submodule
setattr(google_mod, 'genai', genai)
sys.modules['google'] = google_mod
sys.modules['google.generativeai'] = genai_mod
# also make "google.generativeai" point to an object that has the same API
setattr(genai_mod, 'genai', genai)

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
