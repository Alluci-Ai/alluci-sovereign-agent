
import asyncio
import json
import logging
import torch
from datetime import datetime, timezone
from typing import Dict, Any, Callable
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

# PPN & DPK Integration
from .inference.ppn import PPNEmbeddingModule
from .security.dpk import DiscreteProjectionKernel, PolytopeState

class ExecutiveOrchestrator:
    def __init__(self, router: ModelRouter, vault: VaultManager, ace: AffectiveEngine, settings: Settings, skill_manager: SkillManager = None):
        self.settings = settings
        self.logger = logging.getLogger("Orchestrator")
        self.vault = vault
        self.skill_manager = skill_manager
        
        # Sub-systems
        self.identity = SovereignIdentity(settings)
        self.planner = Planner(router)
        self.critic = Critic(router, settings.CRITIC_THRESHOLD)
        self.adapter_registry = AdapterRegistry()
        self.harmonic = HarmonicAssistant() # Harmonic Enhancer Integration
        self.ace = ace
        
        # PPN / DPK Initialization
        self.ppn = PPNEmbeddingModule(input_dim=384, latent_dim=384) 
        self.dpk = DiscreteProjectionKernel()
        
        # Heartbeat System
        self.heartbeat = HeartbeatDaemon(self, vault)
        self.heartbeat_task = None
        
        # Executor
        self.executor = Executor(
            self.adapter_registry, 
            session_factory=lambda: db_engine,
            max_concurrent=settings.MAX_CONCURRENT_TASKS
        )

    async def start_background_services(self):
        self.logger.info("Background services started.")
        self.heartbeat_task = asyncio.create_task(self.heartbeat.start())

    async def stop_background_services(self):
        if self.heartbeat_task:
            self.heartbeat.stop()
            await self.heartbeat_task
        self.logger.info("Background services stopped.")

    def _build_system_context(self) -> str:
        """
        Constructs the cognitive context for the Planner based on the 
        active Soul Manifest (Identity, Cognition) and Verified Skills.
        """
        context_parts = []
        
        # 1. Identity & Cognition Layer
        try:
            manifest = self.vault.retrieve_secret("soul_manifest")
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

    def _perform_ppn_check(self, objective: str, autonomy: str) -> bool:
        """
        Runs the Polytope Projection Network and Discrete Projection Kernel
        to verify manifold integrity before planning.
        """
        try:
            # 1. Embed Objective (Lazy load sentence transformer)
            # In production, we'd use a dedicated embedding service
            if not hasattr(self, "_embed_model"):
                from sentence_transformers import SentenceTransformer
                self._embed_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Generate real embedding of the objective
            embedding = self._embed_model.encode(objective, convert_to_tensor=True)
            # Batch size 10 to simulate a cloud of thought vectors for the PPN
            input_tensor = embedding.unsqueeze(0).expand(10, -1)
            
            # 2. Get Affective Tension (Psi)
            psi = 0.5
            if self.ace.current_state.get("stress_score", 0) > 50:
                psi = 0.8
            
            # 3. PPN Forward Pass
            # Returns: Adjacency(G), Deformation(D), Betti(B), Points
            G, D, B, _ = self.ppn(input_tensor, psi=psi)
            
            # 4. Extract Simplicial Counts (V, E, F)
            V, E, F = self.ppn.extract_simplex_counts(G)
            
            # 5. Construct Polytope State
            # Use hash of objective as signature_hash surrogate
            sig_hash = abs(hash(objective)) 
            betti_list = B.tolist()
            
            state = PolytopeState(
                signature_hash=sig_hash,
                vertices_V=V,
                edges_E=E,
                faces_F=F,
                betti=betti_list,
                affective_tension_psi=psi
            )
            
            # 6. DPK Authorization
            return self.dpk.authorize_execution(state)

        except Exception as e:
            self.logger.error(f"PPN/DPK Check Failed: {e}")
            # Fail closed if security check errors out
            return False

    async def execute_objective(self, objective: str, autonomy: str) -> Dict[str, Any]:
        self.logger.info(f"🚀 EXECUTING SOVEREIGN OBJECTIVE: {objective}")

        # 1. PPN / DPK Manifold Check
        is_manifold_stable = self._perform_ppn_check(objective, autonomy)
        if not is_manifold_stable:
             self.logger.critical("🛑 MANIFOLD TEARING DETECTED via PPN/DPK. Execution Halted.")
             return {
                 "status": "halted",
                 "reason": "Manifold stability check failed (PPN/DPK)",
                 "error_code": "MANIFOLD_INTEGRITY_VIOLATION",
                 "diagnostics": {
                     "objective_complexity": len(objective),
                     "autonomy_level": autonomy,
                     "check": "Polytopological Persistence Network",
                 },
                 "recovery": [
                     "Reduce objective complexity — break it into smaller sub-tasks.",
                     "Lower the autonomy level to RESTRICTED to enable additional safety gates.",
                     "Reset the Affective Engine via POST /telemetry with neutral biometrics.",
                     "Check system health via GET /system/status and resolve any UNSTABLE providers.",
                     "If the issue persists, rotate vault keys via POST /api/vault/rotate to reset manifold state.",
                 ],
             }

        # 2. Create DB Run Record
        run_id = self._create_run_record(objective, autonomy)

        # 3. Affective Gate
        if autonomy == "RESTRICTED" and self.ace.should_throttle():
             self._update_run_status(run_id, RunStatus.FAILED, feedback="Biometric Throttle")
             return {"status": "halted", "reason": "Biometric stress limit reached."}

        # 4. Planning
        try:
            # Inject Identity & Skills into Planning Context
            system_context = self._build_system_context()
            
            tasks = await self.planner.generate_plan(objective, context=system_context)
            
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
        final_output = ""
        critic_score = 0.0
        
        for attempt in range(self.settings.MAX_AUTONOMY_RETRIES):
            self.logger.info(f"--- 🔄 Cycle {attempt + 1} ---")
            
            # Execute
            updated_tasks = await self.executor.execute_dag(run_id, tasks)
            
            # Check Results
            failed_tasks = [t.id for t in updated_tasks.values() if t.status == TaskStatus.FAILED]
            results_summary = json.dumps({t.id: t.result for t in updated_tasks.values()}, indent=2)
            
            # Critique
            passed, score, feedback = await self.critic.evaluate(objective, results_summary)
            
            if passed and not failed_tasks:
                self._update_run_status(run_id, RunStatus.COMPLETED, score=score, feedback=feedback)
                return {
                    "run_id": run_id,
                    "status": "success",
                    "result": results_summary,
                    "score": score,
                    "manifest": signed_manifest
                }
            
            # Self-Correction
            if attempt < self.settings.MAX_AUTONOMY_RETRIES - 1:
                try:
                    tasks = await self.planner.refine_plan(
                        objective, current_plan, results_summary, feedback, failed_tasks
                    )
                    current_plan = [t.dict() for t in tasks.values()]
                except Exception as e:
                    self.logger.error(f"Refinement failed: {e}")
                    break
        
        self._update_run_status(run_id, RunStatus.FAILED, score=critic_score, feedback=feedback)
        return {
            "run_id": run_id,
            "status": "failed",
            "reason": "Max retries exceeded",
            "score": critic_score,
            "feedback": feedback
        }

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
                if score: run.score = score
                if feedback: run.feedback = feedback
                session.add(run)
                session.commit()

    def _save_manifest(self, run_id: int, signature: str):
        with Session(db_engine) as session:
            run = session.get(Run, run_id)
            if run:
                run.manifest_signature = signature
                session.add(run)
                session.commit()
