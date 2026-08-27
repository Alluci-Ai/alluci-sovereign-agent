import os
import time
import json
import uuid
import asyncio
from typing import List, Dict, Any, Optional, Union, AsyncGenerator
from pydantic import BaseModel, Field
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

from ..logging_config import get_logger
from ..inference.mlx_engine import MLXEngine

logger = get_logger("V1CompatRouter")

router = APIRouter(tags=["OpenAI Compatibility Bridge"])


class ChatMessage(BaseModel):
    role: str
    content: Union[str, List[Dict[str, Any]]] = ""
    name: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = "mlx-community/GLM-4-32B-0414-4bit"
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0
    max_tokens_limit: Optional[int] = Field(default=8192, alias="max_tokens")
    stream: Optional[bool] = False
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None


def _extract_prompt_and_system(messages: List[ChatMessage]) -> tuple[str, str]:
    """Separates system instructions from user/assistant conversation history."""
    system_parts = []
    conversation_turns = []

    for msg in messages:
        # Extract text content safely if passed as string or multimodal blocks
        if isinstance(msg.content, str):
            text = msg.content
        elif isinstance(msg.content, list):
            text_blocks = [b.get("text", "") for b in msg.content if isinstance(b, dict) and b.get("type") == "text"]
            text = "\n".join(text_blocks)
        else:
            text = str(msg.content)

        if msg.role == "system":
            system_parts.append(text)
        elif msg.role == "user":
            conversation_turns.append(f"User: {text}")
        elif msg.role == "assistant":
            conversation_turns.append(f"Assistant: {text}")
        elif msg.role == "tool":
            conversation_turns.append(f"Tool Output ({msg.name or 'tool'}): {text}")
        else:
            conversation_turns.append(f"{msg.role}: {text}")

    system_instruction = "\n\n".join(system_parts)
    full_prompt = "\n\n".join(conversation_turns) if conversation_turns else "Hello"
    return full_prompt, system_instruction


@router.get("/models")
@router.get("/v1/models")
async def list_models() -> Dict[str, Any]:
    """
    OpenAI-compatible model list endpoint.
    Scans local mirror_cache/ for available sovereign models.
    """
    models_list = []
    base_cache_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "mirror_cache"))

    if os.path.exists(base_cache_dir):
        for item in sorted(os.listdir(base_cache_dir)):
            item_path = os.path.join(base_cache_dir, item)
            if os.path.isdir(item_path) and not item.startswith("."):
                # Exclude internal non-model utility folders
                if item in ("embeddings", "tmp"):
                    continue
                models_list.append({
                    "id": item,
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "alluci-sovereign-mlx",
                    "permission": [],
                    "root": item,
                    "parent": None
                })

    # Ensure default GLM and Gemma representations exist even if mirror_cache has subdirectories
    default_ids = [
        "mlx-community/GLM-4-32B-0414-4bit",
        "mlx-community/GLM-4-32B-0414-8bit",
        "mlx-community/GLM-4-9B-0414-8bit",
        "mlx-community/glm-4-9b-chat-1m-6bit",
        "mlx-community/GLM-4.1V-9B-Thinking-4bit",
        "mlx-community/GLM-4.6V-4bit",
        "mlx-community/GLM-4.7-4bit"
    ]
    for def_id in default_ids:
        if not any(m["id"] == def_id for m in models_list):
            models_list.append({
                "id": def_id,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "alluci-sovereign-mlx",
                "permission": [],
                "root": def_id,
                "parent": None
            })

    return {
        "object": "list",
        "data": models_list
    }


@router.post("/chat/completions")
@router.post("/v1/chat/completions")
async def create_chat_completion(request: Request, body: ChatCompletionRequest):
    """
    OpenAI-compatible chat completion endpoint.
    Powered 100% on-device by Apple Silicon MLXEngine.
    """
    engine = MLXEngine()
    prompt, system_instruction = _extract_prompt_and_system(body.messages)
    req_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created_ts = int(time.time())

    logger.info(f"[ V1Compat ] Received completion request for model: {body.model} (stream={body.stream})")

    if body.stream:
        async def stream_generator() -> AsyncGenerator[str, None]:
            try:
                # Initial role chunk
                initial_chunk = {
                    "id": req_id,
                    "object": "chat.completion.chunk",
                    "created": created_ts,
                    "model": body.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"role": "assistant", "content": ""},
                            "finish_reason": None
                        }
                    ]
                }
                yield f"data: {json.dumps(initial_chunk)}\n\n"

                max_gen_length = body.max_tokens_limit or 8192
                gen_opts = {"max_tokens": max_gen_length}
                async for chunk_str in engine.generate_stream(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    temperature=body.temperature or 0.7,
                    tools=body.tools,
                    **gen_opts
                ):
                    if chunk_str:
                        chunk_payload = {
                            "id": req_id,
                            "object": "chat.completion.chunk",
                            "created": created_ts,
                            "model": body.model,
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {"content": chunk_str},
                                    "finish_reason": None
                                }
                            ]
                        }
                        yield f"data: {json.dumps(chunk_payload)}\n\n"

                # Final completion chunk
                final_chunk = {
                    "id": req_id,
                    "object": "chat.completion.chunk",
                    "created": created_ts,
                    "model": body.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }
                    ]
                }
                yield f"data: {json.dumps(final_chunk)}\n\n"
                yield "data: [DONE]\n\n"

            except Exception as stream_err:
                logger.error(f"[ V1Compat ] Streaming generation error: {stream_err}")
                error_payload = {
                    "error": {
                        "message": str(stream_err),
                        "type": "server_error",
                        "code": 500
                    }
                }
                yield f"data: {json.dumps(error_payload)}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    else:
        try:
            max_gen_length = body.max_tokens_limit or 8192
            gen_opts = {"max_tokens": max_gen_length}
            generated_text = await engine.generate(
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=body.temperature or 0.7,
                tools=body.tools,
                **gen_opts
            )

            prompt_tokens = max(1, len(prompt) // 4)
            completion_tokens = max(1, len(generated_text) // 4)

            return JSONResponse(content={
                "id": req_id,
                "object": "chat.completion",
                "created": created_ts,
                "model": body.model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": generated_text
                        },
                        "finish_reason": "stop"
                    }
                ],
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens
                }
            })
        except Exception as e:
            logger.error(f"[ V1Compat ] Non-streaming generation error: {e}")
            raise HTTPException(status_code=500, detail=f"Local MLX Generation Error: {str(e)}")
