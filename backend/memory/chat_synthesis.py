"""
H-LSM Chat History Synthesis & Reduction Engine
=================================================

Performs asynchronous multi-turn conversation synthesis and memory reduction.
Compresses raw chat sessions into high-density semantic summary nodes for L2 vector storage
and L3 topological graph linkage.
"""

from __future__ import annotations
import asyncio
import json
import time
import uuid
import hashlib
from typing import Dict, List, Any, Optional
from ..logging_config import get_logger

logger = get_logger("ChatSynthesis")

class ChatSynthesisEngine:
    """
    Asynchronous memory reduction worker for session histories.
    """
    def __init__(self, settings: Any = None):
        self.settings = settings

    async def synthesize_session(
        self,
        session_key: str,
        messages: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Processes a list of chat message turns and returns a structured memory reduction payload.
        """
        if not messages or len(messages) < 2:
            logger.debug(f"[SYNTHESIS] Session {session_key[:8]} has insufficient turns for reduction.")
            return None

        now = time.time()
        session_hash = hashlib.sha256(f"{session_key}_{now}".encode()).hexdigest()[:12]

        user_messages = [m.get("content", "") for m in messages if m.get("role") == "user" or m.get("sender") == "user"]
        assistant_messages = [m.get("content", "") for m in messages if m.get("role") in ["assistant", "model"] or m.get("sender") in ["assistant", "alluci"]]

        # Extract topics and key decisions
        topics: List[str] = []
        for msg in user_messages:
            words = [w.strip(".,!?").title() for w in msg.split() if len(w) > 4 and w.isalpha()]
            topics.extend(words[:3])

        unique_topics = list(dict.fromkeys(topics))[:5]
        topic_summary = ", ".join(unique_topics) if unique_topics else "General Strategic Discussion"

        # Construct high-density semantic summary block
        summary_text = (
            f"Session {session_key[:8]} Summary [{topic_summary}]:\n"
            f"• Interaction Volume: {len(messages)} turns ({len(user_messages)} user queries, {len(assistant_messages)} responses).\n"
            f"• Core Focus: {topic_summary}.\n"
            f"• Key User Inputs: {user_messages[0][:150] if user_messages else 'N/A'}\n"
            f"• Resolution Highlights: {assistant_messages[-1][:200] if assistant_messages else 'N/A'}"
        )

        synthesis_payload = {
            "id": f"synth_{session_hash}",
            "session_key": session_key,
            "created_at": now,
            "topic_summary": topic_summary,
            "summary_content": summary_text,
            "turn_count": len(messages),
            "source": "chat_synthesis",
            "metadata": {
                "user_queries_count": len(user_messages),
                "topics": unique_topics
            }
        }

        logger.info(f"[SYNTHESIS] Successfully synthesized session {session_key[:8]} into semantic node {synthesis_payload['id']}")
        return synthesis_payload
