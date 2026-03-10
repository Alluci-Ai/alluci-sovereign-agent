import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Set, Tuple, Optional
import structlog
from sqlmodel import Session

from .models import TaskStatus, Run, RunStatus
from .inference.router import ModelRouter
from .security.vault import VaultManager
from .ace.engine import AffectiveEngine
from .config import Settings
from .security.verus import SovereignIdentity
from .database import engine as db_engine

# Engine Modules
from .engine.planner import Planner
from .engine.executor import Executor
from .engine.critic import Critic
from .adapters.registry import AdapterRegistry
from .harmonic_enhancer import HarmonicAssistant
from .heartbeat import HeartbeatDaemon
from .skill_manager import SkillManager

from .security.dpk import DiscreteProjectionKernel, PolytopeState
from .security.avl_gate import AVLGate
from .ace.entropy_monitor import EntropySpikeDetector
from .inference.kcm import KCMGeodesicCost
from .security.health_monitor import PVTManifoldHealthMonitor
from .security.audit_log import TopologicalAuditLog
from .ace.memory_decay import MemoryTopologyDecay
from .inference.ppn import PPNEmbeddingModule

class ExecutiveOrchestrator:
    def __init__(self, router: ModelRouter, vault: VaultManager, ace: AffectiveEngine, 
                 settings: Settings, skill_manager: SkillManager = None, 
                 approval_manager=None, analytics=None, vault_root: str = None,
                 memory_manager = None):
        self.settings = settings
        self.logger = logging.getLogger("ExecutiveOrchestrator")
        self.vault = vault
        self.skill_manager = skill_manager
        self.approval_manager = approval_manager
        self.analytics = analytics
        self.memory = memory_manager
        
        # Sub-systems
        self.identity = SovereignIdentity(settings)
        self.planner = Planner(router)
        self.critic = Critic(router, settings.CRITIC_THRESHOLD)
        self.adapter_registry = AdapterRegistry(vault_root=vault_root, memory_manager=memory_manager, on_inbound=self.handle_inbound_message)
        self.harmonic = HarmonicAssistant() # Harmonic Enhancer Integration
        self.ace = ace
        
        self.ppn = PPNEmbeddingModule(input_dim=384, latent_dim=384) 
        self.dpk = DiscreteProjectionKernel()
        self.avl = AVLGate()
        self.entropy_monitor = EntropySpikeDetector()
        self.geodesic_cost = KCMGeodesicCost()
        self.health_monitor = PVTManifoldHealthMonitor()
        self.audit_log = TopologicalAuditLog()
        self.memory_decay = MemoryTopologyDecay()
        
        # Heartbeat System
        self.heartbeat = HeartbeatDaemon(self, vault)
        self.heartbeat_task = None
        self._ws_gateway = None
        
    @property
    def ws_gateway(self):
        return self._ws_gateway

    @ws_gateway.setter
    def ws_gateway(self, val):
        self._ws_gateway = val
        if self.heartbeat:
            self.heartbeat.ws_gateway = val
        
        # Executor
        self.executor = Executor(
            self.adapter_registry, 
            session_factory=lambda: db_engine,
            max_concurrent=settings.MAX_CONCURRENT_TASKS,
            approval_manager=self.approval_manager
        )

    async def start_background_services(self):
        self.logger.info("Background services started.")
        self.heartbeat_task = asyncio.create_task(self.heartbeat.start())

    async def stop_background_services(self):
        if self.heartbeat_task:
            self.heartbeat.stop()
            await self.heartbeat_task
        self.logger.info("Background services stopped.")

    async def handle_inbound_message(self, message: Dict[str, Any]):
        """
        Process a message received from a connected channel adapter.
        Turns the message body into an autonomous objective.
        """
        body = message.get("body", "").strip()
        sender = message.get("from", "unknown")
        protocol = message.get("protocol", "UNKNOWN")
        account_id = message.get("account_id")
        session_key = message.get("session_key", f"inbound_{int(datetime.now().timestamp())}")

        if not body:
            return

        self.logger.info(f"[Orchestrator] Inbound {protocol} message from {sender} (Account: {account_id}): {body[:50]}...")
        
        # 1. Record User Message to Log & Set Context
        with structlog.contextvars.bound_contextvars(session_key=session_key):
            if self.analytics:
                self.analytics.record_message(
                    session_key=session_key,
                    role="user",
                    content=body,
                    account_id=account_id
                )

            # Trigger autonomous execution
            try:
                # Treats inbound message as a new objective.
                # Injects account context into the objective for the planner/executor
                routing_context = f" via {protocol} account {account_id}" if account_id else ""
                
                result = await self.execute_objective(
                    objective=f"Respond to {protocol} message from {sender}: {body}{routing_context}",
                    autonomy="autonomous"
                )

                # 2. Record Assistant Response to Log
                if self.analytics:
                    self.analytics.record_message(
                        session_key=session_key,
                        role="assistant",
                        content=str(result),
                        account_id=account_id
                    )

            except Exception as e:
                self.logger.error(f"[Orchestrator] Error handling inbound message: {e}")
                if self.analytics:
                    self.analytics.record_message(
                        session_key=session_key,
                        role="system",
                        content=f"Error: {e}"
                    )

    async def _build_system_context(self) -> str:
        """
        Constructs the cognitive context for the Planner based on the 
        active Soul Manifest (Identity, Cognition) and Verified Skills.
        """
        context_parts = []
        
        # 1. Identity & Cognition Layer
        try:
            manifest = await self.vault.retrieve_secret("soul_manifest")
            if manifest:
                id_core = manifest.get("identityCore", "You are an autonomous agent.")
                reasoning = manifest.get("reasoningStyle", "Analytical.")
                frameworks = manifest.get("frameworks", [])
                mindsets = manifest.get("mindsets", [])
                methodologies = manifest.get("methodologies", [])
                logic = manifest.get("logic", [])
                cots = manifest.get("chainsOfThought", [])
                best_practices = manifest.get("bestPractices", [])
                
                context_parts.append(f"IDENTITY CORE: {id_core}")
                context_parts.append(f"REASONING STYLE: {reasoning}")
                
                if frameworks:
                    context_parts.append(f"MENTAL FRAMEWORKS: {', '.join(frameworks)}")
                if mindsets:
                    context_parts.append(f"MINDSETS: {', '.join(mindsets)}")
                if methodologies:
                    context_parts.append(f"METHODOLOGIES: {', '.join(methodologies)}")
                if logic:
                    context_parts.append(f"CORE LOGIC: {', '.join(logic)}")
                if cots:
                    context_parts.append(f"PREFERRED CHAINS OF THOUGHT: {'; '.join(cots)}")
                if best_practices:
                    context_parts.append(f"BEST PRACTICES: {'; '.join(best_practices)}")

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

        except Exception:
            pass

        # 2. Skills Layer
        if self.skill_manager:
            try:
                skills = self.skill_manager.list_skills()
                active_skills = [s for s in skills if s.get("verified", False)]
                if active_skills:
                    context_parts.append("AVAILABLE COGNITIVE MODULES (SKILLS):")
                    for s in active_skills:
                        context_parts.append(f"- {s['name']}: {s['description']}")
                        if 'logic' in s and s['logic']:
                            context_parts.append(f"  Logic: {', '.join(s['logic'])}")
            except Exception:
                pass
                
        return "\n".join(context_parts)

    def _perform_ppn_check(self, objective: str, autonomy: str) -> Tuple[bool, Optional[PolytopeState]]:
        """
        Runs the Polytope Projection Network and Discrete Projection Kernel
        to verify manifold integrity before planning.
        """
        try:
            # 1. Embed Objective
            if not hasattr(self, "_embed_model"):
                from sentence_transformers import SentenceTransformer
                self._embed_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            embedding = self._embed_model.encode(objective, convert_to_tensor=True)
            input_tensor = embedding.unsqueeze(0).expand(10, -1)
            
            # 2. Get Affective State (PPN-001/002)
            affect_state = self.ace.get_affective_state()
            psi = self.ace.btm.psi_from_state(affect_state)
            
            # 3. PPN Forward Pass (Updated Signature for Sprint 2)
            # Returns: G, D, B, Points, Phi, Budget, Coherence, Entropy, Stability, Shift
            G, D, B, _, phi_total, budget, coherence, h_norm, delta_b_norm, _ = self.ppn(input_tensor, psi=psi, affect_state=affect_state)
            
            # 4. Extract Simplicial Counts (V, E, F)
            V, E, F = self.ppn.extract_simplex_counts(G)
            
            # 5. Construct Polytope State
            chi = V - E + F
            sig_hash = self.dpk.compute_signature_hash(B.tolist(), chi)
            
            state = PolytopeState(
                signature_hash=sig_hash,
                vertices_V=V,
                edges_E=E,
                faces_F=F,
                betti=B.tolist(),
                affective_tension_psi=psi,
                phi_total=phi_total,
                coherence=coherence,
                budget_used=budget
            )
            
            # 6. DPK Authorization
            is_valid = self.dpk.authorize_execution(state)
            
            # 7. Entropy Spike Detection (PPN-007)
            # Find graph entropy from h_norm (Normalized Graph Entropy)
            self.entropy_monitor.push(h_norm)
            
            return is_valid, state

        except Exception as e:
            self.logger.error(f"PPN/DPK Check Failed: {e}")
            # Fail closed if security check errors out
            return False, None

    async def execute_objective(self, objective: str, autonomy: str, mode: str = "standard") -> Dict[str, Any]:
        self.logger.info(f"🚀 EXECUTING SOVEREIGN OBJECTIVE ({mode.upper()} MODE): {objective}")

        if mode == "research":
            return await self.execute_research(objective)

        # 1. PPN / DPK Manifold Check
        is_manifold_stable, polytope_state = self._perform_ppn_check(objective, autonomy)
        if not is_manifold_stable:
             self.logger.critical("🛑 MANIFOLD TEARING DETECTED via PPN/DPK. Execution Halted.")
             return {
                 "status": "halted",
                 "reason": "Manifold stability check failed (PPN/DPK)",
                 # ... existing diagnostics ...
             }
        
        # 1a. PVT Health Monitor (AAP-004)
        if polytope_state:
            health_report = self.health_monitor.evaluate(polytope_state)
            if health_report["status"] == "CRITICAL":
                self.logger.critical(f"🛑 CRITICAL MANIFOLD HEALTH: {health_report['issues']}")
                # Continue for now, but in strict mode we could halt.

        # 2. Create DB Run Record
        run_id = self._create_run_record(objective, autonomy)

        # 3. Affective Gate
        if autonomy == "RESTRICTED" and self.ace.should_throttle():
             self._update_run_status(run_id, RunStatus.FAILED, feedback="Biometric Throttle")
             return {"status": "halted", "reason": "Biometric stress limit reached."}

        # 4. Planning
        try:
            # Inject Identity & Skills into Planning Context
            system_context = await self._build_system_context()
            
            # 4a. Context Window Compaction Phase
            # Estimate token count (rough heuristic: ~4 chars per token)
            estimated_tokens = len(system_context) // 4
            # Dynamic context window limit based on settings (default 8000 for safety buffer)
            context_limit = getattr(self.settings, 'MAX_CONTEXT_TOKENS', 8000)
            
            if estimated_tokens > context_limit:
                self.logger.warning(f"Context manifold ({estimated_tokens} tokens) exceeds boundary ({context_limit}). Compacting...")
                # Perform conceptual trimming (take the latter half/most recent plus core identity)
                # In a true RAG system, this would compress via summarization
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

            tasks = await self.planner.generate_plan(objective, context=system_context, psi=psi)
            
            # --- Harmonic Ranking Hook ---
            # Prioritize tasks based on Topological and Lattice dynamics
            task_list = list(tasks.values())
            ranked_list = self.harmonic.rank_actions(task_list)
            
            # Log the ranking for observability
            self.logger.info(f"Harmonic Ranking Applied: {[t.id for t in ranked_list]}")
            
            current_plan = [t.dict() for t in ranked_list]
            self._update_run_status(run_id, RunStatus.ACTIVE)
        except Exception as e:
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
            "timestamp": asyncio.get_event_loop().time()
        })
        self._save_manifest(run_id, signed_manifest.get("signature"))
        self.logger.info(f"📜 Manifest Signed by {signed_manifest['signer']}")

        # 6. Execution Loop
        critic_score = 0.0
        start_time = time.time()
        
        for attempt in range(self.settings.MAX_AUTONOMY_RETRIES):
            # PPN-011: Turn Deadline Affective Contraction
            # If a cycle takes > 30s, inject tension for next cycle.
            elapsed = time.time() - start_time
            if elapsed > 30.0:
                self.logger.warning("🕒 Cycle latency breach. Injecting affective contraction (PPN-011).")
                self.ace.inject_deadline_contraction(turns=1)

            self.logger.info(f"--- 🔄 Cycle {attempt + 1} ---")
            
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
            
            # --- Audit Logging (AAP-005) ---
            if polytope_state and hasattr(self, "geodesic_cost"):
                # Goal Betti is conceptually [1, 1, 1] for a stable 3D manifold
                goal_betti = torch.tensor([1, 1, 1])
            if polytope_state:
                if hasattr(self, "geodesic_cost"):
                    # Goal Betti is conceptually [1, 1, 1] for a stable 3D manifold
                    goal_betti = torch.tensor([1, 1, 1])
                    drift = self.geodesic_cost.compute(
                        torch.tensor(polytope_state.betti), 
                        goal_betti, 
                        psi=polytope_state.affective_tension_psi
                    )
                    self.logger.info(f"📈 Manifold Geodesic Drift: {drift:.4f}")
                self.audit_log.log_entry(objective, polytope_state, results_summary)
           
            # --- AVL Security Gate (PPN-006) ---
            # Verify the completion against the manifold state
            if polytope_state:
                is_safe, avl_reason = self.avl.verify(results_summary, polytope_state)
                if not is_safe:
                    self.logger.critical(f"🛑 REJECTED BY AVL: {avl_reason}")
                    self._update_run_status(run_id, RunStatus.FAILED, feedback=f"AVL Rejection: {avl_reason}")
                    return {
                        "run_id": run_id,
                        "status": "failed",
                        "reason": avl_reason,
                        "error_code": "AVL_SECURITY_VIOLATION"
                    }

            # Self-Correction
            if attempt < self.settings.MAX_AUTONOMY_RETRIES - 1:
                # AAP-007: ψ-Gated Continuous Autonomy.
                # If tension is too high, prevent autonomous self-correction loop.
                if psi > 0.9:
                    self.logger.critical("🛑 CONTINUOUS AUTONOMY BLOCKED (High Tension). Requesting manual intervention.")
                    self._update_run_status(run_id, RunStatus.FAILED, feedback="Autonomy Gated: High affective tension")
                    break

                try:
                    tasks = await self.planner.refine_plan(
                        objective, current_plan, results_summary, feedback, failed_tasks
                    )
                    current_plan = [t.dict() for t in tasks.values()]
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
        """
        Autonomous Research Pipeline:
        1. Deconstruct -> 2. Search -> 3. Fetch -> 4. Synthesize
        """
        self.logger.info(f"🔍 Starting Autonomous Research: {objective}")
        
        # Phase 1: Planning / Deconstruction
        plan_prompt = f"Deconstruct this research objective into 3-5 specific search queries: {objective}. Return as a JSON list of strings."
        queries_json = await self.planner.router.get_response(plan_prompt, complexity="MEDIUM")
        try:
            queries = json.loads(queries_json)
            if not isinstance(queries, list): queries = [objective]
        except:
            queries = [objective]

        research_results = []
        
        # Phase 2: Search & Fetch
        for query in queries[:3]: # Limit to top 3 queries for safety
            self.logger.info(f"🌐 Searching: {query}")
            search_tool = self.adapter_registry.get_adapter("web_search")
            search_data = await search_tool.execute({"query": query})
            
            # Fetch top 2 results
            links = [res["link"] for res in search_data.get("results", [])[:2]]
            for link in links:
                self.logger.info(f"📄 Fetching: {link}")
                fetch_tool = self.adapter_registry.get_adapter("web_fetch")
                content = await fetch_tool.execute({"url": link})
                research_results.append({
                    "source": link,
                    "content": content.get("text", "")[:5000] # Cap content per source
                })

        # Phase 3: Synthesis
        synthesis_prompt = f"""
        Objective: {objective}
        Research Data: {json.dumps(research_results)}
        
        Synthesize a professional, grounded research report. 
        Cite sources by their source index.
        """
        report = await self.planner.router.get_response(synthesis_prompt, complexity="HIGH")
        
        return {
            "status": "success",
            "result": report,
            "sources": [r["source"] for r in research_results]
        }

    async def multi_agent_delegate(self, agent_id: str, task: str) -> Dict[str, Any]:
        """
        Delegates a task to a virtual sub-agent in the constellation.
        """
        self.logger.info(f"🤖 Delegating to agent '{agent_id}': {task}")
        # In this sprint, we treat delegation as a specialized system-prompt injection
        delegated_objective = f"[SYSTEM: Act as Specialist Agent {agent_id}] Objective: {task}"
        return await self.execute_objective(delegated_objective, autonomy="autonomous")

    async def compact_all_memory(self):
        """
        Daily Cron Task: Summarizes memories from the last 24h into a single fragment.
        """
        self.logger.info("🧹 Starting Memory Compaction Manifold...")
        if not self.memory:
            self.logger.warning("Memory Manager not available for compaction.")
            return

        memories = await self.memory.get_recent(limit=100)
        
        if not memories:
            return
            
        # Filter: only summarize raw fragments (not already syntheses)
        fragments = [m for m in memories if m["metadata"].get("type") != "daily_synthesis"]
        if not fragments:
            self.logger.info("No fresh memory fragments to compact.")
            return

        content_to_summarize = "\n---\n".join([f"[{m['metadata'].get('timestamp')}]: {m['content']}" for m in fragments])
        
        prompt = f"""
        Summarize the following daily memory fragments into a single, cohesive, long-term 'Daily Synthesis'.
        Retain key technical details, final results of objectives, and important emotional/contextual shifts.
        
        {content_to_summarize}
        """
        
        try:
            synthesis = await self.planner.router.get_response(prompt, complexity="MEDIUM")
            
            # 1. Store Synthesis
            await self.memory.store(synthesis, {
                "type": "daily_synthesis", 
                "compacted_count": len(fragments),
                "original_ids": [m["id"] for m in fragments]
            })
            
            # 2. Delete original fragments to prevent redundancy
            for m in fragments:
                await self.memory.delete(m["id"])
                
            self.logger.info(f"✅ Memory Compaction Complete: {len(fragments)} fragments -> 1 Daily Synthesis.")
        except Exception as e:
            self.logger.error(f"Memory Compaction Failed: {e}")
 
    # --- Persistence Methods ---
    def _create_run_record(self, objective: str, autonomy: str) -> int:
        with Session(db_engine) as session:
            run = Run(objective=objective, autonomy_level=autonomy, status=RunStatus.QUEUED)
            session.add(run)
            session.commit()
            session.refresh(run)
            return run.id

    def _update_run_status(self, run_id: int, status: str, score: float = 0.0, feedback: str = None):
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
