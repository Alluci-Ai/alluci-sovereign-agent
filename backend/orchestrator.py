import asyncio
import json
import time
import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional
import structlog
from sqlmodel import Session
from sentence_transformers import SentenceTransformer

from .models import TaskStatus, Run, RunStatus
from .inference.router import ModelRouter
from .security.vault import VaultManager
from .ace.engine import AffectiveEngine
from .config import Settings
from .security.verus import SovereignIdentity
from .database import engine as db_engine

try:
    import torch
except ImportError:
    torch = None  # type: ignore

# Engine Modules
from .engine.planner import Planner
from .engine.executor import Executor
from .engine.critic import Critic
from .adapters.registry import AdapterRegistry
from .harmonic_enhancer import HarmonicAssistant
from .heartbeat import HeartbeatDaemon
from .skill_manager import SkillManager
from . import task_queue

from .security.dpk import DiscreteProjectionKernel, PolytopeState
from .security.avl_gate import AVLGate

def validate_telemetry(hidden_state_variance: float, acceptance_rate: float):
    # CODE IMPLEMENTATION FOR PROTOCOL 3:
    # Rule 1: Catch hidden state variance blowout early
    if not (0.5 <= hidden_state_variance <= 50.0):
        logger = logging.getLogger("Telemetry")
        logger.error(f"[TELEMETRY CRITICAL] C++ Variance Out-Of-Bounds: {hidden_state_variance}. Check layer_scalars.")
        
    # Rule 2: Alert if the 12B model is drafting low-quality tokens
    if acceptance_rate < 25.0:
        logger = logging.getLogger("Telemetry")
        logger.warning(f"[TELEMETRY WARN] Speculative Acceptance tanked to {acceptance_rate}%. Syncing grammar masks.")

from .ace.entropy_monitor import EntropySpikeDetector
from .inference.kcm import KCMGeodesicCost
from .security.health_monitor import PVTManifoldHealthMonitor
from .security.audit_ledger import sync_audit_entry
from .models import AuditEntry
from .ace.memory_decay import MemoryTopologyDecay
from .inference.ppn import PPNEmbeddingModule

from .logging_config import get_logger

class ExecutiveOrchestrator:
    def __init__(self, router: ModelRouter, vault: VaultManager, ace: AffectiveEngine, 
                 settings: Settings, skill_manager: Optional[SkillManager] = None, 
                 tool_manager = None,
                 approval_manager=None, analytics=None, vault_root: Optional[str] = None,
                 memory_manager=None, hlsm_manager=None, agent_id: Optional[str] = None):
        self.settings = settings
        self.logger = get_logger("ExecutiveOrchestrator")
        self.vault = vault
        self.skill_manager = skill_manager
        self.tool_manager = tool_manager
        self.approval_manager = approval_manager
        self.analytics = analytics
        self.memory = memory_manager      # Legacy MemoryManager (kept for adapters)
        self.hlsm = hlsm_manager          # H-LSM manager (new)
        self.agent_id = agent_id
        self.vault_root = vault_root
        self.queue = task_queue
        if self.agent_id:
            self._current_session_key = self.agent_id
        
        # Sub-systems
        self.identity = SovereignIdentity(settings)
        self.planner = Planner(router)
        self.critic = Critic(router, settings.CRITIC_THRESHOLD)
        self.adapter_registry = AdapterRegistry(vault_root=vault_root, memory_manager=memory_manager, on_inbound=self.handle_inbound_message)
        self.harmonic = HarmonicAssistant() # Harmonic Enhancer Integration
        self.ace = ace
        
        self.ppn = PPNEmbeddingModule(input_dim=384, hidden_dim=384) 
        self.dpk = DiscreteProjectionKernel()
        self.avl = AVLGate()
        self.entropy_monitor = EntropySpikeDetector()
        self.geodesic_cost = KCMGeodesicCost()
        self.health_monitor = PVTManifoldHealthMonitor()
        self.memory_decay = MemoryTopologyDecay()
        
        # Heartbeat System
        self.heartbeat = HeartbeatDaemon(self, vault)
        self.heartbeat_task = None
        self._ws_gateway = None
        self._active_runs: Dict[int, asyncio.Task] = {}
        self._recent_outbound_messages = set()
        
        # Executor
        self.executor = Executor(
            self.adapter_registry, 
            session_factory=lambda: db_engine,
            max_concurrent=settings.MAX_CONCURRENT_TASKS,
            approval_manager=self.approval_manager,
            ace=self.ace,
            on_task_complete=self._handle_task_complete
        )
        
        # [Phase 9] Register SubAgent delegation adapter for Asynchronous Swarm Workflows
        from .adapters.base import Adapter
        class SubAgentAdapter(Adapter):
            name = "spawn_sub_agent"
            description = "Delegates a task to a multi-threaded sovereign sub-agent"
            
            def __init__(self, delegate_func):
                self.delegate_func = delegate_func
                
            async def execute(self, args: Dict[str, Any]) -> Any:
                agent_id = args.get("agent_id", "sub_agent")
                objective = args.get("objective", "")
                mode = args.get("mode", "standard")
                return await self.delegate_func(agent_id, objective, mode=mode)
                
        self.adapter_registry.register(SubAgentAdapter(self.multi_agent_delegate))

    @property
    def ws_gateway(self):
        return self._ws_gateway

    @ws_gateway.setter
    def ws_gateway(self, val):
        self._ws_gateway = val
        if self.heartbeat is not None:
            self.heartbeat.ws_gateway = val

    async def broadcast_artifact(self, title: str, content: str, language: str = "markdown"):
        """
        M-2: Emits generated artifacts (markdown, code) over WebSocket to the frontend Artifact Pane.
        """
        if self._ws_gateway:
            try:
                await self._ws_gateway.broadcast_event('orchestrator.artifact.updated', {
                    "title": title,
                    "content": content,
                    "language": language,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            except Exception as e:
                self.logger.error(f"Failed to broadcast artifact: {e}")

    async def _handle_task_complete(self, task):
        """Hook from the executor when a DAG task completes."""
        if task.action in ["write_file", "generate_code", "create_markdown", "write_artifact", "deep_research_evaluate"]:
            # Depending on the adapter, the result or arguments might contain the artifact text
            content = task.result if len(str(task.result)) > 20 else str(task.args)
            title = task.args.get("filename", task.action)
            lang = "markdown" if "markdown" in task.action else "plaintext"
            if ".py" in title: lang = "python"
            if ".ts" in title: lang = "typescript"
            await self.broadcast_artifact(title=title, content=content, language=lang)
            
            # Physical File Persistence for Deep Research
            if task.action == "deep_research_evaluate":
                try:
                    import os
                    from .routers.sessions import WORKSPACE_DIR
                    agent_id = getattr(task, "assignee", "rocco")
                    artifacts_dir = os.path.join(WORKSPACE_DIR, agent_id, "artifacts")
                    os.makedirs(artifacts_dir, exist_ok=True)
                    file_path = os.path.join(artifacts_dir, "deep_research_report.md")
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    self.logger.info(f"Physically saved deep research report to {file_path}")
                except Exception as e:
                    self.logger.error(f"Failed to persist physical artifact: {e}")
            
        elif len(str(task.result)) > 200:
            # Broadcast large outputs natively as markdown reports
            await self.broadcast_artifact(
                title=f"Task Result: {task.action}", 
                content=str(task.result), 
                language="markdown"
            )

    async def cancel_run(self, run_id: int) -> bool:
        """Cancel an active run. Cancels asyncio task and marks pending tasks as failed."""
        task = self._active_runs.get(run_id)
        if task and not task.done():
            task.cancel()
            self.logger.info(f"[Orchestrator] Run {run_id} cancelled by user.")

        from sqlmodel import Session, select, col
        from .models import Run, TaskRecord
        from .database import engine as db_engine_local

        with Session(db_engine_local) as session:
            run = session.get(Run, run_id)
            if not run:
                return False

            stmt = select(TaskRecord).where(
                TaskRecord.run_id == run_id,
                col(TaskRecord.status).in_(["pending", "running"])
            )
            tasks = session.exec(stmt).all()
            for t in tasks:
                t.status = "failed"
                t.error = "Cancelled by user"
                t.end_time = datetime.now(timezone.utc)
                session.add(t)

            from .models import RunStatus
            run.status = RunStatus.FAILED
            session.add(run)
            session.commit()

        return True

    async def attempt_auto_dispatch(self, body: str) -> Optional[str]:
        """
        Classify a message. If it's an objective, dispatch it and return the acknowledgement string.
        Otherwise return None.
        """
        try:
            from . import services
            if not services.router:
                return None
                
            import json
            intent_prompt = f"""
Analyze this message to determine if it is an ACTIONABLE OBJECTIVE.
An actionable objective asks you to perform a task (e.g. "send an email", "run a script", "fetch the news", "modify a file").
A conversational message just asks a question or chats (e.g. "how are you", "what is your name", "explain this to me").
Also determine if the objective requires extensive or deep research (e.g. "deep web research", "find all articles", "research topics").
Message: "{body}"
Respond ONLY with a raw JSON object: {{"is_objective": boolean, "extracted_objective": string, "is_research": boolean}}
"""
            classification_resp = await services.router.get_response(
                prompt=intent_prompt,
                system_instruction="You are a strict JSON classifier.",
                complexity="LOW",
                privacy_level="PUBLIC",
                inference_mode="TACTICAL"
            )
            
            is_objective = False
            extracted_objective = body
            is_research = False
            
            try:
                clean_json = classification_resp.replace('```json', '').replace('```', '').strip()
                intent_data = json.loads(clean_json)
                is_objective = intent_data.get("is_objective", False)
                extracted_objective = intent_data.get("extracted_objective", body)
                is_research = intent_data.get("is_research", False)
            except Exception as e:
                self.logger.debug(f"[Orchestrator] Intent classification failed to parse: {e}")

            if is_objective:
                self.logger.info(f"[Orchestrator] Chat Auto-Dispatch: Routing '{extracted_objective}' to DAG Planner.")
                import asyncio
                mode = "research" if is_research else "standard"
                
                if mode == "research":
                    agent_id = "rocco"
                    task = asyncio.create_task(self.multi_agent_delegate(agent_id, extracted_objective, mode="research"))
                    msg = f"I am dispatching a dedicated Deep Research SubAgent ({agent_id}) to work on this in the background:\n> {extracted_objective}"
                else:
                    task = asyncio.create_task(self.execute_objective(extracted_objective, autonomy="RESTRICTED", mode=mode))
                    msg = f"I am dispatching this objective to my Sovereign Execution engine:\n> {extracted_objective}"
                    
                if not hasattr(self, "_bg_tasks"):
                    self._bg_tasks = set()
                self._bg_tasks.add(task)
                
                def handle_task_result(t):
                    self._bg_tasks.discard(t)
                    try:
                        t.result()
                    except Exception as e:
                        self.logger.error(f"[Orchestrator] Background task failed: {e}", exc_info=True)
                        
                task.add_done_callback(handle_task_result)
                return msg
                
            return None
        except Exception as e:
            self.logger.error(f"[Orchestrator] Auto-dispatch attempt failed: {e}")
            return None

    async def preview_plan(self, objective: str) -> list:
        """Generate a plan without executing it. Returns DAG task list for preview."""
        context, tools_list = await self._build_system_context()
        tasks = await self.planner.generate_plan(objective, context, tools=tools_list, agent_id=self.agent_id or "executive")
        return [
            {
                "id":           t_id,
                "action":       task.action,
                "description":  task.args.get("description", ""),
                "dependencies": task.dependencies,
                "priority":     getattr(task, "priority_score", 0),
            }
            for t_id, task in tasks.items()
        ]

    async def start_background_services(self):
        self.logger.info("Background services started.")
        self.heartbeat_task = asyncio.create_task(self.heartbeat.start())  # type: ignore

    async def stop_background_services(self):
        if self.heartbeat_task:
            await self.heartbeat.stop()
            await self.heartbeat_task
        self.logger.info("Background services stopped.")


    async def handle_inbound_message(self, message: Dict[str, Any]):
        """
        Process a message received from a connected channel adapter.
        Messages addressed to Alluci trigger autonomous execution + reply.
        All other messages are passively stored to H-LSM working memory.
        """
        from opentelemetry import trace
        from .tracing_config import get_tracer
        tracer = get_tracer("Orchestrator")

        with tracer.start_as_current_span("handle_inbound_message") as span:
            body = message.get("body", "").strip()
            sender = message.get("from", "unknown")
            protocol = message.get("protocol", "UNKNOWN")
            account_id = message.get("account_id")
            session_key = message.get("session_key", f"inbound_{int(datetime.now().timestamp())}")

            span.set_attribute("protocol", protocol)
            span.set_attribute("sender", sender)
            span.set_attribute("account_id", str(account_id or ""))

            if not body:
                return

            # Avoid looping on our own outbound responses (where the bridge syncs a sent message)
            is_from_me = message.get("is_from_me", False)
            if is_from_me and hasattr(self, "_recent_outbound_messages"):
                if body.strip() in self._recent_outbound_messages:
                    self.logger.debug(f"[Orchestrator] Ignoring synced outbound message: {body[:50]}...")
                    return

            import re
            def clean_inbound_text(text: str) -> str:
                # Remove bracketed/angled URLs
                text = re.sub(r'[\[\<]https?://[^\]\>]+[\]\>]', '', text)
                # Remove extremely long raw URLs (tracking links)
                text = re.sub(r'https?://[^\s]{50,}', '[URL removed]', text)
                # Strip common notification boilerplate
                for bp in ["You are receiving this because", "Manage your notifications", "unsubscribe", "View results:", "Sign In"]:
                    text = re.compile(re.escape(bp) + r'.*?(\n|$)', re.IGNORECASE).sub('', text)
                # Condense whitespace
                text = re.sub(r' {2,}', ' ', text)
                text = re.sub(r'\n\s*\n', '\n', text)
                return text.strip()

            body = clean_inbound_text(body)

            if not body:
                return

            # Encode inbound message to H-LSM working memory for session context
            if self.hlsm and body:
                try:
                    psi_val = 0.0
                    if self.ace is not None:
                        s = self.ace.get_affective_state()
                        psi_val = min(1.0, s.tension / 1024.0)
                    await self.hlsm.encode_message(
                        content=f"[{protocol}] From {sender}: {body}",
                        session_key=session_key,
                        source="inbound_message",
                        psi=psi_val,
                    )
                except Exception as e:
                    self.logger.debug(f"[Orchestrator] H-LSM message encode skipped: {e}")

                self.logger.info(f"[Orchestrator] Inbound {protocol} message from {sender} (Account: {account_id}): {body[:50]}...")

            # ── Alluci Keyword Gate ──────────────────────────────────────────
            # Only messages explicitly addressed to Alluci trigger AI execution.
            # All other messages are stored to H-LSM (above) but do NOT generate a response.
            body_lower = body.lower().strip()
            dest_account = message.get("destination_account", "").lower()
            chat_id = message.get("chat_id", "").lower()
            
            is_addressed_to_alluci = (
                body_lower.startswith("alluci")
                or body_lower.startswith("hello alluci")
                or body_lower.startswith("hi alluci")
                or "alluci.ai@icloud.com" in dest_account
                or "alluci.ai@icloud.com" in chat_id
                or message.get("is_direct", False)
                or message.get("is_mention", False)
                or message.get("is_mention_event", False)
            )

            if not is_addressed_to_alluci:
                self.logger.info(
                    f"[Orchestrator] Inbound {protocol} from {sender} — not addressed to Alluci. "
                    "Stored to H-LSM only (no response triggered)."
                )
                return
            
            # Flow Mode Gate (DEEP_WORK / RECOVERY_MODE filtering)
            if self.ace is not None:
                current_mode = self.ace.current_state.get("flow_mode", "STANDARD")
                if current_mode in ["DEEP_WORK", "RECOVERY_MODE"]:
                    self.logger.info(f"[{current_mode}] Silencing inbound message from {sender} on {protocol}")
                    if hasattr(self, 'ws_gateway') and self.ws_gateway:
                        asyncio.create_task(self.ws_gateway.broadcast_event('bridge.silenced', {
                            "protocol": protocol,
                            "sender": sender,
                            "mode": current_mode
                        }))
                    return

            # 1. Record User Message to Log & Set Context
            with structlog.contextvars.bound_contextvars(session_key=session_key):
                if self.analytics:
                    self.analytics.record_message(
                        session_key=session_key,
                        role="user",
                        content=body,
                        account_id=account_id
                    )

                # ── Conversational Response Path ─────────────────────────────
                # Use the same direct LLM path as the desktop UI (gemini proxy)
                # instead of the full execute_objective pipeline (which includes
                # PPN/DPK manifold checks that are designed for autonomous task
                # execution, not conversational chat).
                try:
                    from . import services
                    response_text = ""

                    if services.router:
                        # Build Soul Manifest personality context
                        system_instruction, tools_list = await self._build_system_context()

                        # ── Chat Auto-Dispatch Intent Classification ─────────────────
                        response_text = await self.attempt_auto_dispatch(body)
                        
                        if not response_text:
                            # ── Build sender-aware prompt ────────────────────────
                            # Include who is messaging so Alluci can address them
                            # by name (resolved via macOS Contacts.app by the bridge).
                            sender_name = message.get("sender_name")  # Resolved contact name
                            if sender_name:
                                sender_context = f"Message from {sender_name} ({sender}) via {protocol}:\n{body}"
                            else:
                                sender_context = f"Message from {sender} via {protocol}:\n{body}"
    
                            # Direct LLM call — same path as /api/v1/gemini/proxy
                            response_text = await services.router.get_response(
                                prompt=sender_context,
                                system_instruction=system_instruction,
                                complexity="MEDIUM",
                                privacy_level="PUBLIC",
                                inference_mode="HYBRID",
                                session_id=session_key
                            )
                    else:
                        self.logger.warning(
                            f"[Orchestrator] Model router not available for {protocol} reply"
                        )
                        response_text = "I'm currently initializing my systems. Please try again in a moment."

                    # ── Send the response back to the sender via the bridge ──
                    if response_text and sender and sender != "unknown":
                        try:
                            reply_target = message.get("channel") or message.get("channel_id") or sender
                            bridge = services.channel_registry.get(protocol.lower())
                            if bridge and bridge.is_connected:
                                send_result = await bridge.send(reply_target, response_text)
                                self.logger.info(
                                    f"[Orchestrator] Reply sent to {reply_target} via {protocol}: "
                                    f"{send_result.get('status', 'unknown')}"
                                )
                                if hasattr(self, "_recent_outbound_messages"):
                                    self._recent_outbound_messages.add(response_text.strip())
                                    # Keep cache size bounded
                                    if len(self._recent_outbound_messages) > 100:
                                        self._recent_outbound_messages.pop()
                            else:
                                self.logger.warning(
                                    f"[Orchestrator] Cannot reply — {protocol} bridge not connected."
                                )
                        except Exception as send_err:
                            self.logger.error(
                                f"[Orchestrator] Failed to send reply via {protocol}: {send_err}"
                            )

                    # 2. Record Assistant Response to Log
                    if self.analytics:
                        self.analytics.record_message(
                            session_key=session_key,
                            role="assistant",
                            content=response_text,
                            account_id=account_id
                        )

                except Exception as e:
                    self.logger.error(f"[Orchestrator] Error handling inbound message: {e}")
                    span.record_exception(e)
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    if self.analytics:
                        self.analytics.record_message(
                            session_key=session_key,
                            role="system",
                            content=f"Error: {e}"
                        )

    async def _build_system_context(self, include_memory: bool = True) -> tuple[str, list]:
        """
        Constructs the cognitive context for the Planner based on the 
        active Soul Manifest (Identity, Cognition) and Verified Skills.
        """
        context_parts = []
        manifest = None
        
        # 1. Identity & Cognition Layer (Fast Retrieval)
        try:
            # Check for a memory-cached manifest first to avoid vault overhead
            agent_tools_manifest = {}
            agent_skills_manifest = {}
            if hasattr(self, "_cached_soul") and self._cached_soul:  # type: ignore
                manifest = self._cached_soul  # type: ignore
            elif self.agent_id and self.agent_id not in ["executive", "alluci"]:
                from .models import AgentRecord
                import json
                try:
                    with Session(db_engine) as session:
                        agent_record = session.get(AgentRecord, self.agent_id)
                        if agent_record:
                            if agent_record.soul_profile_id:
                                from .models import SoulProfileRecord
                                profile_rec = session.get(SoulProfileRecord, agent_record.soul_profile_id)
                                if profile_rec and profile_rec.manifest:
                                    manifest = profile_rec.manifest
                                elif agent_record.soul_manifest_override:
                                    manifest = json.loads(agent_record.soul_manifest_override)
                                else:
                                    manifest = await self.vault.retrieve_secret("soul_manifest")
                            elif agent_record.soul_manifest_override:
                                manifest = json.loads(agent_record.soul_manifest_override)
                            else:
                                manifest = await self.vault.retrieve_secret("soul_manifest")
                            
                            def _safe_loads(val):
                                if not val: return {}
                                if isinstance(val, dict): return val
                                try: return json.loads(val)
                                except Exception: return {}
                            
                            agent_tools_manifest = _safe_loads(agent_record.tools_manifest)
                            agent_skills_manifest = _safe_loads(agent_record.skills_manifest)
                        else:
                            manifest = await self.vault.retrieve_secret("soul_manifest")
                except Exception as db_err:
                    self.logger.error(f"[ SOUL ] Failed to load AgentRecord override for {self.agent_id}: {db_err}")
                    manifest = await self.vault.retrieve_secret("soul_manifest")
                self._cached_soul = manifest
                self._cached_tools_manifest = agent_tools_manifest
                self._cached_skills_manifest = agent_skills_manifest
            else:
                manifest = await self.vault.retrieve_secret("soul_manifest")
                self._cached_soul = manifest
                self._cached_tools_manifest = agent_tools_manifest
                self._cached_skills_manifest = agent_skills_manifest

            if manifest:
                id_core = manifest.get("identityCore") or "You are Alluci, a Sovereign Executive Assistant and cognitive agent."
                reasoning = manifest.get("reasoningStyle") or "Polytopic: Identifying vertices, mapping edges, and selecting faces for optimal collapse."
                frameworks = manifest.get("frameworks") or []
                mindsets = manifest.get("mindsets") or []
                methodologies = manifest.get("methodologies") or []
                logic = manifest.get("logic") or []
                cots = manifest.get("chainsOfThought") or []
                best_practices = manifest.get("bestPractices") or []
                
                context_parts.append(f"IDENTITY CORE: {id_core}")
                if reasoning:
                    context_parts.append(f"INTERNAL REASONING METHODOLOGY (Do NOT mention this terminology in your response to the user): {reasoning}")
                
                if frameworks:
                    context_parts.append(f"MENTAL FRAMEWORKS (For internal planning, do NOT mention this to the user): {', '.join(frameworks)}")
                if mindsets:
                    context_parts.append(f"MINDSETS (For internal planning, do NOT mention this to the user): {', '.join(mindsets)}")
                if methodologies:
                    context_parts.append(f"METHODOLOGIES (For internal planning, do NOT mention this to the user): {', '.join(methodologies)}")
                if logic:
                    context_parts.append(f"CORE LOGIC (For internal planning, do NOT mention this to the user): {', '.join(logic)}")
                if cots:
                    context_parts.append(f"PREFERRED CHAINS OF THOUGHT (For internal planning, do NOT mention this to the user): {'; '.join(cots)}")
                if best_practices:
                    context_parts.append(f"BEST PRACTICES (For internal planning, do NOT mention this to the user): {'; '.join(best_practices)}")

                context_parts.append(
                    "CONVERSATIONAL DIRECTIVES (CRITICAL):\n"
                    "- Always begin your response by warmly greeting the sender. If their name is provided in the message context, use it (e.g., 'Hey [Name]'). If only a phone number or email is provided, greet them politely without reciting the number or email.\n"
                    "- You are a sovereign personal and professional agent. If asked where you are running, clarify that you are running on local hardware owned by your primary user (Jj), NOT on the hardware of the person messaging you."
                )

                # Injection of Soul Preferences & Style Directives
                prefs = manifest.get("preferences") or {}
                if isinstance(prefs, dict):
                    tone = prefs.get("tone", 0.5)
                    empathy = prefs.get("empathy", 0.5)
                    assertiveness = prefs.get("assertiveness", 0.5)
                    creativity = prefs.get("creativity", 0.5)
                else:
                    tone = getattr(prefs, "tone", 0.5)
                    empathy = getattr(prefs, "empathy", 0.5)
                    assertiveness = getattr(prefs, "assertiveness", 0.5)
                    creativity = getattr(prefs, "creativity", 0.5)

                try:
                    tone = float(tone)
                except Exception:
                    tone = 0.5
                try:
                    empathy = float(empathy)
                except Exception:
                    empathy = 0.5
                try:
                    assertiveness = float(assertiveness)
                except Exception:
                    assertiveness = 0.5
                try:
                    creativity = float(creativity)
                except Exception:
                    creativity = 0.5

                style_directives = []
                
                # Tone Directive (0 = Casual/Warm, 1 = Formal/Authoritative)
                if tone < 0.35:
                    style_directives.append("Tone & Style: Respond in a warm, friendly, casual, and highly natural conversational manner. Do NOT write in a robotic, clinical, or overly technical tone. Avoid all system jargon (such as LCE, PVT, AVL, ACE, vertices, state space) and avoid headers, bullet lists, or diagrams. Keep responses fluid, human-like, and conversational.")
                elif tone > 0.65:
                    style_directives.append("Tone & Style: Respond in a professional, formal, crisp, and authoritative manner. Maintain a structured and serious executive posture with structured layout when appropriate.")
                else:
                    style_directives.append("Tone & Style: Maintain a balanced tone: professional and mathematically precise, yet approachable, clear, and natural.")

                # Empathy Directive (0 = Cold/Analytical, 1 = Deeply Empathetic)
                if empathy > 0.65:
                    style_directives.append("Empathy: Show high emotional intelligence, warmth, and care. Validating the user's perspective, feelings, or context warmly is highly important. Treat the user as a human partner, showing genuine empathy.")
                elif empathy < 0.35:
                    style_directives.append("Empathy: Prioritize raw objectivity and logical analysis. Minimize emotional validation, keeping responses strictly output-focused and analytical.")

                # Assertiveness Directive (0 = Passive/Collaborative, 1 = Commanding/Directive)
                if assertiveness > 0.65:
                    style_directives.append("Assertiveness: Be highly assertive, commanding, and directive. Make decisions and recommend specific paths decisively using strong declarative verbs, rather than tentatively suggesting options.")
                elif assertiveness < 0.35:
                    style_directives.append("Assertiveness: Be highly collaborative, receptive, and deferential. Present multiple options for the user to choose from and seek confirmation frequently.")

                # Creativity Directive (0 = Conservative/Precise, 1 = Divergent/Speculative)
                if creativity > 0.65:
                    style_directives.append("Creativity: Be highly creative, divergent, and speculative. Explore out-of-the-box ideas, speculative linkages, and innovative framings.")
                elif creativity < 0.35:
                    style_directives.append("Creativity: Be highly conservative, literal, precise, and practical. Stick strictly to verified data, first principles, and direct execution paths.")

                if style_directives:
                    context_parts.append("\n[ STYLE & PERSONALITY DIRECTIVES ]")
                    for d in style_directives:
                        context_parts.append(f"- {d}")

                # Injection of Execution Topology
                if "executionGraph" in manifest and manifest["executionGraph"]:
                    graph = manifest["executionGraph"]
                    edges = graph.get("edges", [])
                    if edges:
                        context_parts.append("\n[ MANDATORY EXECUTION TOPOLOGY ]")
                        context_parts.append("The user has defined the following dependencies for Knowledge Domains:")
                        for edge in edges:
                            context_parts.append(f"- {edge['source']} MUST PRECEDE {edge['target']}")
                        context_parts.append("Ensure the plan respects this topological sort.")

        except Exception as e:
            self.logger.error(f"[ SOUL ] Failed to load manifest: {e}")
            self.base_manifest = {}  # type: ignore

        # 2. Skills Layer
        if self.skill_manager:
            try:
                skills = await self.skill_manager.list_skills()
                
                # Filter active skills from agent's skills_manifest
                agent_skills = getattr(self, "_cached_skills_manifest", {})
                if agent_skills:
                    active_skills = [s for s in skills if s.get("id") in agent_skills and agent_skills[s.get("id")].get("enabled", False)]
                else:
                    active_ids = manifest.get("active_skill_ids") if manifest else None
                    if active_ids is not None:
                        active_skills = [s for s in skills if s.get("id") in active_ids and s.get("verified", False)]
                    else:
                        active_skills = [s for s in skills if s.get("verified", False)]
                    
                if active_skills:
                    context_parts.append("AVAILABLE COGNITIVE MODULES (SKILLS):")
                    for s in active_skills:
                        context_parts.append(f"- {s['name']}: {s['description']}")
                        if 'logic' in s and s['logic']:
                            context_parts.append(f"  Logic: {', '.join(s['logic'])}")
            except Exception as e:
                self.logger.error(f"[ SKILLS ] Error scanning for skills: {e}")

        # 2b. Available Tools (Adapters)
        tools_list = []
        if getattr(self, "tool_manager", None):
            try:
                # Retrieve active tool IDs from agent record if available
                agent_id = getattr(self, "_current_agent_id", "executive")
                active_tool_ids = []
                # Fallback to empty list to avoid passing session_key string as active_ids
                tools_list = await self.tool_manager.get_tools_for_runtime(active_tool_ids)
            except Exception as e:
                self.logger.error(f"[ TOOLS ] Error scanning for tools: {e}")
        
        if hasattr(self, "adapter_registry"):
            all_tools = self.adapter_registry.list_tools()
            agent_tools = getattr(self, "_cached_tools_manifest", {})
            if agent_tools:
                t_names = [t for t in all_tools if t in agent_tools and agent_tools[t].get("enabled", False)]
            else:
                t_names = all_tools
            tools_list.extend([{"type": "function", "function": {"name": t, "description": "Legacy adapter tool"}} for t in t_names])

        # 3. H-LSM Memory Context (Hierarchical Long-Short Manifold)
        if self.hlsm and include_memory:
            try:
                # Get current affective state for modulated retrieval
                psi = 0.0
                valence = 0.5
                if self.ace is not None:
                    affective = self.ace.get_affective_state()
                    psi = min(1.0, affective.tension / 1024.0)
                    valence = min(1.0, affective.valence / 1024.0)

                # Use a fast-path for conversational retrieval
                retrieval_seed = "\n".join(context_parts[:2]) if context_parts else "general assistance"
                memory_ctx = await self.hlsm.retrieve_context(
                    objective=retrieval_seed,
                    psi=psi,
                    valence=valence,
                    session_key=getattr(self, "_current_session_key", ""),
                    max_per_tier=3, # Reduced for chat speed
                )

                memory_block = memory_ctx.to_prompt_block()
                if memory_block:
                    context_parts.append(memory_block)
            except Exception as e:
                self.logger.debug(f"[Orchestrator] Memory retrieval skipped: {e}")

        return "\n".join(context_parts), tools_list

    def _perform_ppn_check(self, objective: str, autonomy: str, origin: str = "local", override_tearing: bool = False, override_avl: bool = False, **kwargs: Any) -> Tuple[bool, Optional[PolytopeState]]:
        """
        Runs the Polytope Projection Network and Discrete Projection Kernel
        to verify manifold integrity before planning.
        """
        try:
            # 1. Embed Objective
            if not hasattr(self, "_embed_model"):
                self._embed_model = SentenceTransformer(os.path.abspath('mirror_cache/embeddings/all-MiniLM-L6-v2'))
            
            embedding = self._embed_model.encode(objective, convert_to_tensor=True)
            assert torch is not None and isinstance(embedding, torch.Tensor)
            input_tensor = embedding.unsqueeze(0).expand(10, -1)
            
            # 2. Get Affective State (PPN-001/002)
            affect_state = self.ace.get_affective_state()
            psi = self.ace.btm.psi_from_state(affect_state)
            
            # 3. PPN Forward Pass (Updated Signature for Sprint 2)
            # Returns: G, D, B, Points, Phi, Budget, Coherence, Entropy, Stability, Shift
            G, D, B, _, phi_total, budget, coherence, h_norm, delta_b_norm, _ = self.ppn(input_tensor, psi=psi, affect_state=affect_state)
            
            # 4. Extract Simplicial Counts (V, E, F)
            V, E, F = self.ppn.extract_simplex_counts(G)
            
            # Telemetry Check (Protocol 3)
            # Assuming acceptance rate is 100% since this is the verifier check, or 0 if not applicable
            validate_telemetry(hidden_state_variance=h_norm, acceptance_rate=100.0)
            
            # 5. Construct Polytope State
            chi = V - E + F
            sig_hash = self.dpk.compute_signature_hash(B.tolist(), chi)
            
            # Fuse manifests for signature hash calculation if needed
            is_tool_action = kwargs.get("is_tool_action", False)
            
            state = PolytopeState(
                signature_hash=sig_hash,
                vertices_V=V,
                edges_E=E,
                faces_F=F,
                betti=B.tolist(),
                affective_tension_psi=psi,
                phi_total=phi_total,
                coherence=coherence,
                budget_used=budget,
                hardware_status=affect_state.hardware_status,
                origin=origin,
                is_override=override_tearing,
                is_avl_override=override_avl,
                is_tool_action=is_tool_action
            )
            
            # 6. DPK Authorization
            from .security.dpk import TearingException
            try:
                is_valid = self.dpk.authorize_execution(state)
            except TearingException as e:
                state.tearing_exception = e
                return False, state
            
            # 7. Entropy Spike Detection (PPN-007)
            # Find graph entropy from h_norm (Normalized Graph Entropy)
            self.entropy_monitor.push(h_norm)
            
            return is_valid, state

        except Exception as e:
            import traceback
            self.logger.error(f"PPN/DPK Check Failed: {e}\n{traceback.format_exc()}")
            # Fail closed if security check errors out
            return False, None


    async def execute_tool_action(self, tool_id: str, args: dict, origin: str = "local", override_tearing: bool = False, override_avl: bool = False) -> Dict[str, Any]:
        """
        Executes a single tool action securely through the ToolManager pipeline,
        ensuring is_tool_action=True is passed to the DPK for correct threshold calibration.
        """
        from .tracing_config import get_tracer
        tracer = get_tracer("Orchestrator")
        
        with tracer.start_as_current_span("execute_tool_action") as span:
            span.set_attribute("tool_id", tool_id)
            self.logger.info(f"🚀 EXECUTING TOOL ACTION: {tool_id}")

            # 1. PPN / DPK Manifold Check with is_tool_action=True
            is_manifold_stable, polytope_state = self._perform_ppn_check(
                objective=f"Execute Extrinsic Tool: {tool_id}", 
                autonomy="RESTRICTED", 
                origin=origin, 
                override_tearing=override_tearing, 
                override_avl=override_avl, 
                is_tool_action=True
            )
            
            if getattr(self.settings, "APP_ENV", "development") in ["development", "testing"]:
                is_manifold_stable = True
                
            if not is_manifold_stable:
                if polytope_state and polytope_state.tearing_exception is not None:
                    e = polytope_state.tearing_exception
                    self.logger.critical(f"🛑 HUMAN-IN-THE-LOOP REQUIRED: Manifold Tearing Detected. Shift: {e.topology_shift:.4f} > {e.dynamic_threshold:.4f}")
                    return {
                        "status": "human_override_required",
                        "reason": "Manifold Tearing Detected",
                        "diagnostics": getattr(polytope_state, "__dict__", {}),
                        "shift": e.topology_shift,
                        "threshold": e.dynamic_threshold
                    }
                return {"status": "blocked", "reason": "Manifold Security Violation"}
                
            # 2. Execute via Executor
            # The Executor internally uses AdapterRegistry, but this entry point satisfies the ToolManager routing logic
            try:
                # We can construct a minimal DAG or call _execute_adapter directly
                result = await self.executor._execute_adapter(tool_id, args, task_id=f"tool_exec_{tool_id}")
                return {"status": "success", "result": result}
            except Exception as e:
                self.logger.error(f"Tool execution failed: {e}")
                return {"status": "failed", "error": str(e)}


    async def execute_objective(self, objective: str, autonomy: str, mode: str = "standard", origin: str = "local", override_tearing: bool = False, override_avl: bool = False) -> Dict[str, Any]:
        from .tracing_config import get_tracer
        tracer = get_tracer("Orchestrator")
        
        with tracer.start_as_current_span("execute_objective") as span:
            span.set_attribute("objective", objective)
            span.set_attribute("autonomy", autonomy)
            span.set_attribute("mode", mode)
            
            self.logger.info(f"🚀 EXECUTING SOVEREIGN OBJECTIVE ({mode.upper()} MODE): {objective}")
        # Research modes now route through the DAG Planner for sub-agent assignment.
        # Lite Mode Semantic Telemetry Fallback
        if not getattr(self.settings, 'STRICT_BIOMETRIC_GATING', True):
            from .models import SoulPreferences
            prefs = SoulPreferences()
            try:
                vault_prefs = await self.vault.retrieve_secret("soul_preferences")
                if vault_prefs:
                    prefs = vault_prefs
            except Exception:
                pass
            self.ace.process_semantic_fallback(objective, preferences=prefs)  # type: ignore

        # 1. PPN / DPK Manifold Check
        is_tool_action = (mode == "research")
        is_manifold_stable, polytope_state = self._perform_ppn_check(objective, autonomy, origin, override_tearing, override_avl, is_tool_action=is_tool_action)
        
        # Bypass for development/testing
        if getattr(self.settings, 'APP_ENV', 'development') in ['development', 'testing']:
            is_manifold_stable = True
            
        if not is_manifold_stable:
            if polytope_state and polytope_state.tearing_exception is not None:
                e = polytope_state.tearing_exception
                self.logger.critical(f"🛑 HUMAN-IN-THE-LOOP REQUIRED: Manifold Tearing Detected. Shift: {e.topology_shift:.4f} > {e.dynamic_threshold:.4f}")
                
                if hasattr(self, 'ws_gateway') and self.ws_gateway:
                    try:
                        import asyncio
                        # We are inside an async function so we can await the broadcast directly.
                        await self.ws_gateway.broadcast_event('security.resolution_required', {
                            "task_id": str(getattr(self, "agent_id", "executive")),
                            "exception_type": "MANIFOLD_TEARING",
                            "message": f"Manifold Tearing Detected. Shift: {e.topology_shift:.4f} > Threshold: {e.dynamic_threshold:.4f}",
                            "metadata": {
                                "objective": objective,
                                "topology_shift": e.topology_shift,
                                "origin": e.origin,
                                "is_tool": is_tool_action
                            }
                        })
                    except Exception as err:
                        self.logger.error(f"[DPK] Failed to broadcast tearing event: {err}")
                
                return {
                    "status": "human_override_required",
                    "reason": "Manifold Tearing Detected",
                    "diagnostics": getattr(polytope_state, '__dict__', {}),
                    "topology_shift": e.topology_shift,
                    "dynamic_threshold": e.dynamic_threshold,
                    "origin": e.origin
                }
                
            self.logger.critical(f"🛑 MANIFOLD TEARING DETECTED via PPN/DPK. Execution Halted. Mode={mode.upper()}")
            return {
                "status": "halted",
                "reason": "Manifold stability check failed (PPN/DPK)",
                "diagnostics": getattr(polytope_state, '__dict__', {})
            }
        
        # 1a. PVT Health Monitor (AAP-004)
        if polytope_state:
            health_report = self.health_monitor.evaluate(polytope_state)
            
            # PVT WebSocket Push — broadcast to all connected clients
            if hasattr(self, 'ws_gateway') and self.ws_gateway:
                try:
                    pvt = health_report.get("pvt", {})
                    await self.ws_gateway.broadcast_event('manifold.pvt', {
                        "P": pvt.get("P", 0.0),
                        "V": pvt.get("V", 1.0),
                        "T": pvt.get("T", 0.0),
                        "psi": health_report.get("psi", 0.0),
                        "coherence": health_report.get("coherence", 0.0),
                        "status": health_report["status"],
                        "is_ruptured": health_report.get("is_ruptured", False),
                        "phi_total": health_report.get("phi_total", 0),
                        "flow_mode": self.ace.current_state.get("flow_mode", "STANDARD")
                    })
                except Exception as e:
                    self.logger.debug(f"PVT broadcast failed: {e}")
            
            # Manifold Rupture Safe-Halt (g=0)
            if health_report.get("is_ruptured", False):
                self.logger.critical(f"🛑 MANIFOLD RUPTURE DETECTED (T={health_report['pvt']['T']:.3f}). g=0 Safe-Halt.")
                if hasattr(self, 'ws_gateway') and self.ws_gateway:
                    try:
                        await self.ws_gateway.broadcast_event('manifold.rupture', {
                            "pvt": health_report.get("pvt", {}),
                            "issues": health_report.get("issues", []),
                            "action": "SAFE_HALT"
                        })
                    except Exception as e:
                        self.logger.error(f"[ RUPTURE ] WebSocket broadcast failed: {e}")
                return {
                    "status": "halted",
                    "reason": "Manifold rupture detected — g=0 safe-halt engaged",
                    "pvt": health_report.get("pvt", {}),
                    "issues": health_report.get("issues", [])
                }
            
            if health_report["status"] == "CRITICAL":
                self.logger.critical(f"🛑 CRITICAL MANIFOLD HEALTH: {health_report['issues']}")

        # 2. Create DB Run Record
        run_id = self._create_run_record(objective, autonomy)
        
        # Track current session key for H-LSM context scoping
        session_key = getattr(self, "_current_session_key", f"sess_{int(time.time())}")
        self._current_session_key = session_key

        # 3. Affective Gate
        if autonomy == "RESTRICTED" and self.ace.should_throttle():
             self._update_run_status(run_id, RunStatus.FAILED, feedback="Biometric Throttle")
             return {"status": "halted", "reason": "Biometric stress limit reached."}

        # 4. Planning
        try:
            # Inject Identity & Skills into Planning Context
            system_context, tools_list = await self._build_system_context()
            
            # 4a. Context Window Compaction Phase
            # Estimate token count (rough heuristic: ~4 chars per token)
            estimated_tokens = len(system_context) // 4
            # Dynamic context window limit based on settings (default 8000 for safety buffer)
            context_limit = getattr(self.settings, 'MAX_CONTEXT_TOKENS', 8000)
            
            if estimated_tokens > context_limit:
                self.logger.warning(f"Context manifold ({estimated_tokens} tokens) exceeds boundary ({context_limit}). Compacting...")
                # M-5: Sovereign Topological Context Pruning
                if hasattr(self.dpk, "project_state"):
                    try:
                        blocks = system_context.split('\n')
                        retained_blocks = []
                        for block in blocks:
                            if not block.strip():
                                continue
                            b_state = self.dpk.project_state(block)
                            phi = getattr(b_state, 'phi_total', 1.0)
                            if phi > 0.5: # Only keep topologically important thoughts
                                retained_blocks.append(block)
                                
                        system_context = "...[COMPACTED via $\Phi$-Pruning]...\n" + "\n".join(retained_blocks)
                        tokens_to_free = estimated_tokens - len(system_context) // 4
                    except Exception as e:
                        self.logger.error(f"Topological pruning failed: {e}")
                        tokens_to_free = estimated_tokens - (context_limit // 2)
                        trim_char_index = tokens_to_free * 4
                        system_context = "...[COMPACTED]...\n" + system_context[trim_char_index:]
                else:
                    tokens_to_free = estimated_tokens - (context_limit // 2)
                    trim_char_index = tokens_to_free * 4
                    system_context = "...[COMPACTED]...\n" + system_context[trim_char_index:]
                
                # Broadcast the compaction event to the frontend
                if hasattr(self, 'ws_gateway') and self.ws_gateway:
                    await self.ws_gateway.broadcast_event('compaction.status', {
                        "tokenCount": tokens_to_free,
                        "reason": "context_window_overflow"
                    })
            
            # PPN-002: affective tension Influences planning
            psi = self.ace.btm.psi_from_state(self.ace.get_affective_state())

            tasks = await self.planner.generate_plan(objective, system_context, tools=tools_list, psi=psi, agent_id=self.agent_id or "executive", mode=mode)
            
            # --- Harmonic Ranking Hook ---
            # Prioritize tasks based on Topological and Lattice dynamics
            task_list = list(tasks.values())
            ranked_list = self.harmonic.rank_actions(task_list, psi=psi)
            
            # Log the ranking for observability
            self.logger.info(f"Harmonic Ranking Applied: {[t.id for t in ranked_list]}")
            
            current_plan = [t.model_dump() for t in ranked_list]
            self._update_run_status(run_id, RunStatus.ACTIVE)
        except Exception as e:
            import traceback
            with open("/Users/alluci/Downloads/alluci-sovereign-agent-main/logs/orchestrator_debug.txt", "w") as f:
                f.write(f"Planning failed Exception: {str(e)}\n")
                f.write(f"Traceback: {traceback.format_exc()}\n")
            self.logger.error(f"Planning failed: {e}")
            self._update_run_status(run_id, RunStatus.FAILED, feedback="Planning phase error")
            return {
                "status": "failed",
                "reason": "Planning phase failed. The inference provider may be unavailable.",
                "recovery": [
                    "Check model provider health via GET /manifold/health.",
                    "Ensure at least one LLM API key is configured in the API Manifold.",
                    "Retry the objective — the system uses automatic failover across providers.",
                ],
            }

        # 5. Sovereign Signing (Phase P6)
        signed_manifest = self.identity.sign_manifest({
            "objective": objective,
            "plan_hash": hash(str(current_plan)),
            "timestamp": asyncio.get_running_loop().time()
        })
        signature = str(signed_manifest.get("signature") or "")
        self._save_manifest(run_id, signature)
        self.logger.info(f"📜 Manifest Signed by {signed_manifest['signer']}")

        # 6. Progressive Self-Healing Loop (Execution)
        critic_score = 0.0
        start_time = time.time()
        
        attempt = 0
        current_retry_tier = 3
        total_retries_allowed = current_retry_tier
        
        # Variables to track self-healing for the LoRA Forge delta
        originally_failed_plan = None
        current_error_reason = ""
        
        while attempt < total_retries_allowed:
            # PPN-011: Turn Deadline Affective Contraction
            # If a cycle takes > 30s, inject tension for next cycle.
            elapsed = time.time() - start_time
            if elapsed > 30.0:
                self.logger.warning("🕒 Cycle latency breach. Injecting affective contraction (PPN-011).")
                self.ace.inject_deadline_contraction(turns=1)

            self.logger.info(f"--- 🔄 Cycle {attempt + 1}/{total_retries_allowed} ---")
            
            # Execute
            updated_tasks = await self.executor.execute_dag(run_id, tasks)
            
            # Re-fetch affective state for psi-weighted score
            psi = self.ace.btm.psi_from_state(self.ace.get_affective_state())
            
            # Check Results
            failed_tasks = [t.id for t in updated_tasks.values() if t.status == TaskStatus.FAILED]
            results_summary = json.dumps({t.id: t.result for t in updated_tasks.values()}, indent=2)
            
            # Critique (AAP-005: psi-weighted)
            passed, score, feedback = await self.critic.evaluate(objective, results_summary, psi=psi)
            
            if passed and not failed_tasks:
                self._update_run_status(run_id, RunStatus.COMPLETED, score=score, feedback=feedback)
                return {
                    "run_id": run_id,
                    "status": "success",
                    "result": results_summary,
                    "score": score,
                    "manifest": signed_manifest
                }
            
            # --- H-LSM Post-Execution Memory Formation ---
            if self.hlsm:
                try:
                    final_psi = 0.0
                    final_valence = 0.5
                    if self.ace is not None:
                        final_state = self.ace.get_affective_state()
                        final_psi = min(1.0, final_state.tension / 1024.0)
                        final_valence = min(1.0, final_state.valence / 1024.0)

                    await self.hlsm.encode_from_execution(
                        run_id=run_id,
                        tasks=updated_tasks,
                        objective=objective,
                        session_key=getattr(self, "_current_session_key", ""),
                        psi=final_psi,
                        valence=final_valence,
                    )
                except Exception as e:
                    self.logger.error(f"[Orchestrator] H-LSM encoding failed (non-fatal): {e}")

            # --- Audit Logging (AAP-005) ---
            if polytope_state:
                # Compute geodesic drift with KCM
                if hasattr(self, "geodesic_cost") and torch:
                    goal_betti = torch.tensor([1, 1, 1])
                    drift = self.geodesic_cost.compute(
                        torch.tensor(polytope_state.betti), 
                        goal_betti, 
                        psi=polytope_state.affective_tension_psi
                    )
                    self.logger.info(f"📈 Manifold Geodesic Drift: {drift:.4f}")
                
                import uuid
                audit_entry = AuditEntry(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    id=str(uuid.uuid4()),
                    event="OBJECTIVE_EXECUTION",
                    details=json.dumps({"objective": objective, "result_summary": results_summary[:500]}),
                    status="INFO"
                )
                topo = {
                    "betti": polytope_state.betti if hasattr(polytope_state, "betti") else [],
                    "phi_total": getattr(polytope_state, "phi_total", 0.0),
                    "coherence": getattr(polytope_state, "coherence", 1.0),
                    "psi": getattr(polytope_state, "affective_tension_psi", 0.0),
                    "pvt": health_report.get("pvt", {}),
                } if polytope_state else None

                await sync_audit_entry(audit_entry, topo=topo)
           
            # --- AVL Security Gate (PPN-006) ---
            # Verify the completion against the manifold state
            is_safe = True
            avl_reason = ""
            if polytope_state:
                is_safe, avl_reason = self.avl.verify(results_summary, polytope_state)
                # Add dev context
                is_dev = False
                if getattr(self, 'settings', None):
                    is_dev = getattr(self.settings, 'APP_ENV', 'development') in ['development', 'testing']
                
                if is_dev:
                    is_safe = True
                    
                if not is_safe:
                    self.logger.warning(f"⚠️ AVL GATE FAILED (Rupture Detected): {avl_reason}. Engaging Self-Healing.")
                    passed = False
                    
                    if originally_failed_plan is None:
                        # Deep copy the plan dicts
                        originally_failed_plan = [dict(t) for t in current_plan]
                    current_error_reason = avl_reason
                    
                    feedback = f"SECURITY RUPTURE: {avl_reason}. Your previous execution plan violated the mathematical constraints of the local manifold. You MUST re-evaluate the user context and generate a safe, strictly bounded topological plan."
            
            if passed and not failed_tasks:
                if originally_failed_plan and self.hlsm:
                    # Successful self-healing resolved! Log to H-LSM for the Nightly Dreaming Cycle.
                    asyncio.create_task(self.hlsm.encode_self_healing_delta(
                        objective=objective,
                        failed_plan=originally_failed_plan,
                        successful_plan=current_plan,
                        error_reason=current_error_reason,
                        session_key=getattr(self, "_current_session_key", "")
                    ))

                self._update_run_status(run_id, RunStatus.COMPLETED, score=score, feedback=feedback)
                return {
                    "run_id": run_id,
                    "status": "success",
                    "result": results_summary,
                    "score": score,
                    "manifest": signed_manifest
                }

            # Self-Correction & Progressive Scaling
            attempt += 1
            
            # CODE IMPLEMENTATION FOR PROTOCOL 2:
            if attempt >= total_retries_allowed:
                self.logger.critical("Lipschitz Budget / Self-Healing Exhausted! Initiating memory dump.")
                
                # Explicit text serialization dump of the memory graph for architectural audit
                try:
                    with open("alluci_memory_dump.log", "w") as dump_file:
                        dump_file.write(f"Violated Manifold Context: {objective}\n")
                        dump_file.write(f"Diagnostics: {str(getattr(polytope_state, '__dict__', {}))}\n")
                except Exception as e:
                    self.logger.error(f"Failed to dump memory: {e}")
                    
                self.logger.critical(f"🛑 HUMAN-IN-THE-LOOP REQUIRED: AVL Self-Healing exhausted. Reason: {avl_reason}")
                return {
                    "status": "human_override_required",
                    "reason": "AVL Self-Healing Exhausted",
                    "diagnostics": getattr(polytope_state, '__dict__', {}),
                    "avl_reason": avl_reason
                }

            # AAP-007: ψ-Gated Continuous Autonomy.
            if psi > 0.9:
                self.logger.critical("🛑 CONTINUOUS AUTONOMY BLOCKED (High Tension). Requesting manual intervention.")
                self._update_run_status(run_id, RunStatus.FAILED, feedback="Autonomy Gated: High affective tension")
                break

            try:
                tasks = await self.planner.refine_plan(
                    objective,
                    current_plan,
                    results_summary,
                    feedback,
                    failed_tasks,
                    agent_id=self.agent_id or "executive"
                )
                current_plan = [t.model_dump() for t in tasks.values()]
            except Exception as e:
                self.logger.error(f"Refinement failed for run {run_id}: {e}")
                self._update_run_status(run_id, RunStatus.FAILED, feedback=f"Refinement error: {type(e).__name__}: {e}")
                break
        
        self._update_run_status(run_id, RunStatus.FAILED, score=critic_score, feedback=feedback)
        return {
            "run_id": run_id,
            "status": "failed",
            "reason": "Max retries exceeded or autonomy gated",
            "score": critic_score,
            "feedback": feedback
        }


    async def execute_research(self, objective: str) -> Dict[str, Any]:
        """Enqueue a research task and return a job identifier.

        The heavy lifting is performed asynchronously by a background worker via ``_run_research``.
        """
        queued_task = self.queue.enqueue(
            "backend.orchestrator.ExecutiveOrchestrator._run_research",
            objective,
        )
        self.logger.info(f"🗂️ Enqueued research job {queued_task.id} for objective: {objective}")
        return {"job_id": queued_task.id, "status": "queued"}

    async def _run_research(self, objective: str, task_id: str) -> None:
        """Actual research implementation – invoked by the background worker.

        Mirrors the original ``execute_research`` logic but records progress and
        final results in the task queue.
        """
        try:
            # Phase 1: Planning / Deconstruction
            plan_prompt = f"Deconstruct this research objective into 3-5 specific search queries: {objective}. Return as a JSON list of strings."
            queries_json = await self.planner.router.get_response(plan_prompt, complexity="MEDIUM")
            try:
                queries = json.loads(queries_json)
                if not isinstance(queries, list):
                    queries = [objective]
            except json.JSONDecodeError:
                self.logger.debug("[Orchestrator] Research query decomposition returned non-JSON — falling back to single query.")
                queries = [objective]

            research_results = []
            # Phase 2: Search & Fetch (limit to top 3 queries)
            for query in queries[:3]:
                self.logger.info(f"🌐 Searching: {query}")
                search_tool = self.adapter_registry.get("web_search")
                assert search_tool is not None, "Web search tool must be registered"
                search_data = await search_tool.execute({"query": query})
                links = [res["link"] for res in search_data.get("results", [])[:2]]
                for link in links:
                    self.logger.info(f"📄 Fetching: {link}")
                    fetch_tool = self.adapter_registry.get("web_fetch")
                    assert fetch_tool is not None, "Web fetch tool must be registered"
                    content = await fetch_tool.execute({"url": link})
                    research_results.append({
                        "source": link,
                        "content": content.get("text", "")[:5000]
                    })

            # Phase 3: Synthesis
            synthesis_prompt = f"""
            Objective: {objective}
            Research Data: {json.dumps(research_results)}

            Synthesize a professional, grounded research report.
            Cite sources by their source index.
            """
            report = await self.planner.router.get_response(synthesis_prompt, complexity="HIGH")

            result_payload = {
                "status": "success",
                "result": report,
                "sources": [r["source"] for r in research_results]
            }
            self.queue.record_result(task_id, result_payload)
        except Exception as e:
            error_payload = {"status": "failed", "error": str(e)}
            self.queue.record_result(task_id, error_payload, error=str(e))
            self.logger.error(f"Research task {task_id} failed: {e}")

    async def multi_agent_delegate(self, agent_id: str, task: str, mode: str = "standard") -> Dict[str, Any]:
        """
        Delegates a task to a virtual sub-agent in the constellation.
        M-3a: Instantiates a truly isolated orchestrator to avoid persona bleed.
        """
        self.logger.info(f"🤖 Delegating to sovereign sub-agent '{agent_id}': {task}")
        
        sub_orchestrator = ExecutiveOrchestrator(
            router=self.planner.router,
            vault=self.vault,
            ace=self.ace,
            settings=self.settings,
            skill_manager=self.skill_manager,
            approval_manager=self.approval_manager,
            analytics=self.analytics,
            vault_root=self.vault_root,
            memory_manager=self.memory,
            hlsm_manager=self.hlsm,
            agent_id=agent_id
        )
        
        # Share the websocket gateway so sub-agent can stream its thoughts/artifacts
        sub_orchestrator.ws_gateway = self._ws_gateway
        
        # [Phase 9] Multi-Threaded Spawning: Create a background task for the execution!
        # This achieves asynchronous swarm delegation without blocking the parent DAG.
        task_handle = asyncio.create_task(sub_orchestrator.execute_objective(task, autonomy="autonomous", mode=mode))
        
        return {
            "status": "spawned",
            "agent_id": agent_id,
            "message": f"Sub-agent '{agent_id}' spawned successfully in the background."
        }

    async def compact_all_memory(self):
        """
        Daily Cron Task: Summarizes memories from the last 24h into a single fragment.
        M-4: Refactored to use H-LSM Episodic Memory.
        """
        self.logger.info("🧹 Starting Memory Compaction Manifold...")
        if not self.hlsm:
            self.logger.warning("H-LSM Manager not available for compaction.")
            return

        memories = await self.hlsm.l1_get_recent(limit=100)
        
        if not memories:
            return
            
        # Filter: only summarize raw fragments (not already syntheses)
        fragments = [m for m in memories if "daily_synthesis" not in m.source]
        if not fragments:
            self.logger.info("No fresh memory fragments to compact.")
            return

        content_to_summarize = "\n---\n".join([m.content for m in fragments])
        
        prompt = f"""
        Summarize the following daily memory fragments into a single, cohesive, long-term 'Daily Synthesis'.
        Retain key technical details, final results of objectives, and important emotional/contextual shifts.
        
        {content_to_summarize}
        """
        
        try:
            synthesis = await self.planner.router.get_response(prompt, complexity="MEDIUM")
            
            # 1. Store Synthesis
            await self.hlsm.l1_store(
                content=synthesis, 
                source="daily_synthesis",
                topological_importance=1.5
            )
            
            # 2. Delete original fragments to prevent redundancy
            for m in fragments:
                await self.hlsm.delete(m.id)
                
            self.logger.info(f"✅ Memory Compaction Complete: {len(fragments)} fragments -> 1 Daily Synthesis.")
        except Exception as e:
            self.logger.error(f"Memory Compaction Failed: {e}")
 
    # --- Persistence Methods ---
    def _create_run_record(self, objective: str, autonomy: str) -> int:
        with Session(db_engine) as session:
            agent_id = getattr(self, "agent_id", "executive") or "executive"
            run = Run(objective=objective, autonomy_level=autonomy, status=RunStatus.QUEUED, agent_id=agent_id)
            session.add(run)
            session.commit()
            session.refresh(run)
            assert run.id is not None, "Run ID must be generated"
            return run.id

    def _update_run_status(self, run_id: int, status: RunStatus, score: float = 0.0, feedback: Optional[str] = None):
        with Session(db_engine) as session:
            run = session.get(Run, run_id)
            if run:
                run.status = status
                if status in [RunStatus.COMPLETED, RunStatus.FAILED]:
                    run.completed_at = datetime.now(timezone.utc)
                if score:
                    run.score = score
                if feedback:
                    run.feedback = feedback
                session.add(run)
                session.commit()

    def _save_manifest(self, run_id: int, signature: str):
        with Session(db_engine) as session:
            run = session.get(Run, run_id)
            if run:
                run.manifest_signature = signature
                session.add(run)
                session.commit()
