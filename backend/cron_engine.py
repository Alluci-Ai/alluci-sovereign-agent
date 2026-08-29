"""
Cron Engine for the Polytope Sovereign OS.

Provides three schedule types:
  - interval: run every N minutes/hours/days
  - cron: standard 5-field cron expression
  - run_at: one-shot at a specific ISO datetime

Each job supports per-invocation model overrides, delivery routing
to channel adapters, and a run history log.

Reference: Sovereign Spec Sections 3.1–3.8
"""

import asyncio
from .logging_config import get_logger
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from enum import Enum
from sqlmodel import Session, select, col

logger = get_logger("CronEngine")


class ScheduleType(str, Enum):
    INTERVAL = "interval"
    CRON = "cron"
    RUN_AT = "run_at"


class DeliveryMode(str, Enum):
    ANNOUNCE_SUMMARY = "announce-summary"
    POST_TRANSCRIPT = "post-transcript"
    NONE = "none"


class CronEngine:
    """
    Evaluates due jobs on a tick loop, executes them through the
    orchestrator, and records run history.
    """

    def __init__(self, db_engine, orchestrator=None, channel_registry=None, task_manager=None):
        self.db_engine = db_engine
        self.orchestrator = orchestrator
        self.channel_registry = channel_registry or {}
        self.task_manager = task_manager
        self._running = False
        self._tick_task: Optional[asyncio.Task] = None
        self._tick_interval = 60  # seconds

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def start(self):
        """Start the cron tick loop."""
        if self._running:
            return
        self._running = True
        self._tick_task = asyncio.create_task(self._tick_loop())
        logger.info("[CronEngine] Started")

    async def stop(self):
        """Stop the cron tick loop."""
        self._running = False
        if self._tick_task:
            self._tick_task.cancel()
            try:
                await self._tick_task
            except asyncio.CancelledError:
                pass
        logger.info("[CronEngine] Stopped")

    async def _tick_loop(self):
        """Main loop: evaluate all enabled jobs each tick."""
        while self._running:
            try:
                await self._evaluate_jobs()
                await self._check_overnight_dreaming_cycle()
                await self._refresh_agentic_tokens()
            except Exception as e:
                logger.error(f"[CronEngine] Tick error: {e}")
            await asyncio.sleep(self._tick_interval)

    async def _refresh_agentic_tokens(self):
        """
        Periodically checks agent registrations and uses the refresh token
        to fetch new access tokens before they expire.
        """
        from . import services
        import httpx
        from .auth.autonomous_discoverer import AlluciAutonomousDiscoverer

        if not services.vault:
            return

        domains = await services.vault.list_connections("agent_registration")
        if not domains:
            return

        discoverer = AlluciAutonomousDiscoverer()

        for domain in domains:
            secret = await services.vault.retrieve_connection_secret("agent_registration", domain)
            if not secret or not secret.get("refresh_token"):
                continue

            clean_domain = domain.rstrip('/')
            auth_server_url = clean_domain
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                try:
                    prm_res = await client.get(f"{clean_domain}/.well-known/oauth-protected-resource")
                    if prm_res.status_code == 200:
                        auth_server_url = prm_res.json().get("authorization_server", clean_domain)
                    else:
                        auth_md_res = await client.get(f"{clean_domain}/auth.md")
                        if auth_md_res.status_code == 200:
                            import re
                            match = re.search(r'`?authorization_server`?:\s*`?(https?://[^\s`]+)`?', auth_md_res.text, re.IGNORECASE)
                            if match:
                                auth_server_url = match.group(1)
                except Exception:
                    pass

            token_endpoint = f"{auth_server_url.rstrip('/')}/oauth2/token"
            
            try:
                private_key, _ = await services.vault.get_web_idp_keypair()
                dpop_proof = discoverer._generate_dpop_proof(private_key, "POST", token_endpoint)
                
                payload = {
                    "grant_type": "refresh_token",
                    "refresh_token": secret.get("refresh_token"),
                    "client_id": secret.get("client_id")
                }
                headers = {"DPoP": dpop_proof}

                async with httpx.AsyncClient(timeout=10.0) as token_client:
                    res = await token_client.post(token_endpoint, data=payload, headers=headers)
                    if res.status_code == 200:
                        new_data = res.json()
                        secret["access_token"] = new_data.get("access_token", secret["access_token"])
                        if "refresh_token" in new_data:
                            secret["refresh_token"] = new_data["refresh_token"]
                        if "expires_in" in new_data:
                            secret["expires_in"] = new_data["expires_in"]
                        
                        await services.vault.store_connection_secret("agent_registration", domain, secret)
                        logger.info(f"[CronEngine] Successfully refreshed token for {domain}")
            except Exception as e:
                logger.error(f"[CronEngine] Failed to refresh token for {domain}: {e}")

    async def _check_overnight_dreaming_cycle(self):
        """
        Executes the overnight Self-Instruct and LoRA Forge sequence.

        Production Pipeline (4 Steps):
          1. EXTRACT  — Pull episodic memories (H-LSM), world model (PCL),
                        and affective baseline (ACE) from the live system.
          2. SYNTHESIZE — Use the 31B Dense Teacher model to transform raw
                          memories into high-quality instruction pairs.
          3. VERIFY   — Pass each synthesized pair through PPN → DPK → AVL
                         to cryptographically sign and topologically verify
                         the knowledge before it enters the weights.
          4. FORGE    — Feed verified pairs into LoRAForge with Experience
                         Replay and Elastic Weight Consolidation to permanently
                         bake the day's learnings into the 12B Student model.
        """
        now = datetime.now(timezone.utc)
        # Trigger natively at 2:00 AM UTC
        if now.hour != 2 or now.minute != 0:
            return

        logger.info("[ DREAMING CYCLE ] 2:00 AM UTC — Initiating Overnight Dreaming Cycle.")

        from . import services

        # ─── Gate: Ensure all subsystems are online ───────────────────────
        hlsm = getattr(services, "hlsm_manager", None)
        pcl = getattr(services, "pcl", None)
        ace = getattr(services, "ace_engine", None)
        router = getattr(services, "router", None)
        orch = getattr(services, "orchestrator", None)

        if not hlsm:
            logger.warning("[ DREAMING CYCLE ] H-LSM not available. Aborting.")
            return
        if not router:
            logger.warning("[ DREAMING CYCLE ] Inference Router not available. Aborting.")
            return

        try:
            from .engine.lora_forge import LoRAForge, VRAMHypervisor
            from .engine.dpo_harvester import DPOHarvester

            dpo_harvester = DPOHarvester()

            # ═══════════════════════════════════════════════════════════════
            # STEP 1: EXTRACTION  (H-LSM + PCL + ACE + DPO)
            # ═══════════════════════════════════════════════════════════════
            logger.info("[ DREAMING CYCLE ] Step 1/5: Extracting memories, world model, affective state, and DPO preferences...")

            # 1a. H-LSM: Fetch recent episodic memories (the day's interactions)
            recent_memories = await hlsm.l1_get_recent(limit=50)
            episodic_contents = [
                {"content": m.content, "source": m.source, "relevance": m.relevance_score}
                for m in recent_memories if len(m.content) >= 40
            ]

            # 1b. H-LSM: Fetch self-healing deltas (failed → healed plan pairs)
            self_healing_entries = await hlsm.l1_search("SELF-HEALING RESOLUTION", limit=20)
            healing_contents = [
                {"content": m.content, "source": m.source}
                for m in self_healing_entries
            ]

            # 1c. PCL: Build the current World Model snapshot
            world_model_summary = ""
            if pcl:
                try:
                    world = await pcl.build_world_model()
                    world_parts = []
                    if world.active_goals:
                        world_parts.append(f"Active Goals ({len(world.active_goals)}):")
                        for g in world.active_goals[:10]:
                            world_parts.append(
                                f"  - {g.title} [{g.priority}]: {g.metric_current:.0f}% complete, "
                                f"updated {g.days_since_update:.1f}d ago"
                            )
                    if world.recurring_topics:
                        world_parts.append(f"Recurring Topics: {', '.join(world.recurring_topics[:5])}")
                    if world.recent_learnings:
                        world_parts.append(f"Recent Learnings ({len(world.recent_learnings)}):")
                        for learning in world.recent_learnings[:10]:
                            world_parts.append(f"  - {learning[:200]}")
                    if world.unanswered_threads:
                        world_parts.append(f"Unanswered Threads: {', '.join(world.unanswered_threads[:5])}")
                    world_model_summary = "\n".join(world_parts)
                except Exception as e:
                    logger.warning(f"[ DREAMING CYCLE ] PCL world model extraction failed: {e}")

            # 1d. ACE: Capture current affective baseline
            ace_summary = ""
            if ace:
                try:
                    from .security.calibration import CalibrationManager
                    cal = CalibrationManager()
                    baseline = cal.get_ace_baseline()
                    affective = ace.get_affective_state()
                    flow_mode = ace.current_state.get("flow_mode", "STANDARD")
                    ace_summary = (
                        f"ACE State: Flow={flow_mode}, "
                        f"Valence={affective.valence:.0f}/1024, "
                        f"Arousal={affective.arousal:.0f}/1024, "
                        f"Tension={affective.tension:.0f}/1024, "
                        f"Baseline Mean Stress={baseline['mean']:.1f}, Std={baseline['std']:.1f}"
                    )
                except Exception as e:
                    logger.debug(f"[ DREAMING CYCLE ] ACE baseline extraction failed: {e}")

            # 1e. Quarantine Pool: Fetch failed/rejected coding tasks for DPO preference harvesting
            quarantine_contents = []
            quarantine_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models", "quarantine"))
            if os.path.exists(quarantine_dir):
                for qf in sorted(os.listdir(quarantine_dir))[:15]:
                    if qf.endswith(".json"):
                        try:
                            with open(os.path.join(quarantine_dir, qf), "r", encoding="utf-8") as q_file:
                                q_data = json.load(q_file)
                                quarantine_contents.append(q_data)
                        except Exception:
                            continue

            # 1f. Harvest DPO Preference Triplets (x, y_w, y_l)
            dpo_healing_pairs = dpo_harvester.harvest_from_healing(healing_contents)
            dpo_quarantine_pairs = dpo_harvester.harvest_from_quarantine(quarantine_contents)
            dpo_all_pairs = dpo_healing_pairs + dpo_quarantine_pairs

            # Check if there is enough material to learn from
            total_entries = len(episodic_contents) + len(healing_contents) + len(quarantine_contents)
            if total_entries < 3:
                logger.info(
                    f"[ DREAMING CYCLE ] Insufficient material ({total_entries} entries). "
                    "Skipping tonight's forge cycle."
                )
                return

            logger.info(
                f"[ DREAMING CYCLE ] Extracted {len(episodic_contents)} episodic memories, "
                f"{len(healing_contents)} self-healing deltas, {len(quarantine_contents)} quarantined anti-patterns, "
                f"{len(dpo_all_pairs)} DPO preference pairs, "
                f"PCL world model: {'available' if world_model_summary else 'unavailable'}"
            )

            # ═══════════════════════════════════════════════════════════════
            # STEP 2: SYNTHESIS  (31B Dense Teacher Model)
            # ═══════════════════════════════════════════════════════════════
            logger.info("[ DREAMING CYCLE ] Step 2/5: Synthesizing instruction pairs via Teacher model...")

            # Build the Teacher synthesis prompt from extracted data
            memory_block = "\n".join([
                f"[{e['source']}] {e['content'][:400]}" for e in episodic_contents[:30]
            ])
            healing_block = "\n".join([
                f"[HEALING] {h['content'][:400]}" for h in healing_contents[:10]
            ])
            quarantine_block = "\n".join([
                f"[ANTI-PATTERN REVERTED] Task: {q.get('task_id')} | Description: {q.get('description')} | Reason: {q.get('reason')}"
                for q in quarantine_contents[:10]
            ])

            synthesis_system = (
                "You are the Alluci Knowledge Synthesizer. Your role is to distill "
                "a day's worth of user interactions, episodic memories, self-healing events, "
                "quarantined anti-patterns, and world state into high-quality instruction-response training pairs. "
                "Each pair should capture a reusable insight, behavioral pattern, or knowledge "
                "connection that would improve the agent's future responses.\n\n"
                "Output EXACTLY a JSON array of objects with 'prompt' and 'response' keys. "
                "Generate between 5 and 20 pairs. Focus on:\n"
                "- Patterns in how the user communicates and what they value\n"
                "- Domain knowledge connections the user frequently references\n"
                "- Corrections from self-healing events (what went wrong and the fix)\n"
                "- Quarantined anti-patterns: synthesize correct solutions avoiding the reverted mistakes\n"
                "- Goal-relevant knowledge that would accelerate progress\n\n"
                "Do NOT generate generic or obvious pairs. Every pair must reflect "
                "specific insights from the provided memories."
            )

            synthesis_prompt = (
                f"=== TODAY'S EPISODIC MEMORIES ===\n{memory_block}\n\n"
            )
            if healing_block:
                synthesis_prompt += f"=== SELF-HEALING EVENTS ===\n{healing_block}\n\n"
            if quarantine_block:
                synthesis_prompt += f"=== QUARANTINED ANTI-PATTERNS (NEGATIVE EXAMPLES) ===\n{quarantine_block}\n\n"
            if world_model_summary:
                synthesis_prompt += f"=== WORLD MODEL ===\n{world_model_summary}\n\n"
            if ace_summary:
                synthesis_prompt += f"=== AFFECTIVE BASELINE ===\n{ace_summary}\n\n"
            synthesis_prompt += (
                "Based on the above, generate instruction-response training pairs "
                "as a JSON array. Output ONLY valid JSON."
            )

            # Call the Teacher model via the inference router
            import json as json_mod
            raw_response = await router.get_response(
                prompt=synthesis_prompt,
                system_instruction=synthesis_system,
                complexity="HIGH",
                privacy_level="AIRGAPPED",  # Keep all data local
                inference_mode="LOCAL",     # Force local 31B Dense model
            )

            # Parse the synthesized pairs
            synthetic_pairs: List[Dict[str, Any]] = []
            try:
                # Strip markdown code fences if present
                cleaned = raw_response.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned.rsplit("```", 1)[0]
                cleaned = cleaned.strip()

                parsed = json_mod.loads(cleaned)
                if isinstance(parsed, list):
                    synthetic_pairs = [
                        p for p in parsed
                        if isinstance(p, dict) and "prompt" in p and "response" in p
                    ]
            except (json_mod.JSONDecodeError, ValueError) as e:
                logger.error(f"[ DREAMING CYCLE ] Teacher output parsing failed: {e}")
                logger.debug(f"[ DREAMING CYCLE ] Raw Teacher output: {raw_response[:500]}")
                return

            if not synthetic_pairs:
                logger.warning("[ DREAMING CYCLE ] Teacher produced no valid instruction pairs. Aborting.")
                return

            logger.info(f"[ DREAMING CYCLE ] Teacher synthesized {len(synthetic_pairs)} instruction pairs.")

            # ═══════════════════════════════════════════════════════════════
            # STEP 3: VERIFICATION  (PPN → DPK → AVL)
            # ═══════════════════════════════════════════════════════════════
            logger.info("[ DREAMING CYCLE ] Step 3/5: Verifying synthesized knowledge through PPN/DPK/AVL...")

            verified_pairs: List[Dict[str, Any]] = []
            rejected_count = 0

            if orch and hasattr(orch, "dpk") and hasattr(orch, "avl"):
                for pair in synthetic_pairs:
                    combined_text = f"{pair['prompt']}\n{pair['response']}"
                    try:
                        # Run the full PPN → DPK → AVL pipeline on each pair
                        is_stable, polytope_state = orch._perform_ppn_check(
                            objective=combined_text,
                            autonomy="RESTRICTED",
                            origin="dreaming_cycle"
                        )

                        if polytope_state is not None:
                            is_safe, avl_reason = orch.avl.verify(combined_text, polytope_state)
                            if is_safe:
                                verified_pairs.append(pair)
                            else:
                                rejected_count += 1
                                logger.debug(
                                    f"[ DREAMING CYCLE ] AVL rejected pair: {avl_reason} — "
                                    f"Prompt: {pair['prompt'][:80]}..."
                                )
                        else:
                            # PPN check failed to produce a state — skip pair
                            rejected_count += 1
                            logger.debug(
                                "[ DREAMING CYCLE ] PPN produced no PolytopeState for pair — skipping."
                            )
                    except Exception as e:
                        # Individual pair verification failure is non-fatal
                        rejected_count += 1
                        logger.debug(f"[ DREAMING CYCLE ] Verification error for pair: {e}")
            else:
                # If PPN/DPK/AVL subsystems are not available, pass pairs with warning
                logger.warning(
                    "[ DREAMING CYCLE ] PPN/DPK/AVL subsystems unavailable. "
                    "Passing all pairs through without topological verification."
                )
                verified_pairs = synthetic_pairs

            logger.info(
                f"[ DREAMING CYCLE ] Verification complete: "
                f"{len(verified_pairs)} VERIFIED, {rejected_count} REJECTED"
            )

            if not verified_pairs:
                logger.warning("[ DREAMING CYCLE ] All pairs rejected by AVL. No knowledge to forge tonight.")
                return

            # ═══════════════════════════════════════════════════════════════
            # STEP 4: FORGING & DPO ADAPTERS  (LoRAForge)
            # ═══════════════════════════════════════════════════════════════
            logger.info(
                f"[ DREAMING CYCLE ] Step 4/5: Forging {len(verified_pairs)} verified pairs "
                "into 12B Student model weights and DPO datasets..."
            )

            # Separate into new (today's) and historical (replay buffer) data
            midpoint = max(1, len(verified_pairs) // 2)
            new_data = verified_pairs[:midpoint]
            historical_data = verified_pairs[midpoint:]

            # If we have episodic memories that are older, add them as historical
            if len(episodic_contents) > 20:
                older_memories = [
                    {"prompt": f"Recall: {e['content'][:200]}", "response": e['content'][:400]}
                    for e in episodic_contents[20:]
                ]
                historical_data.extend(older_memories[:10])

            # Determine dominant domain from world model and quarantine signals
            domain = "general"
            if len(quarantine_contents) > 0:
                domain = "codi"
            elif world_model_summary:
                domain_lower = world_model_summary.lower()
                if any(kw in domain_lower for kw in ["code", "python", "script", "debug", "api", "codi"]):
                    domain = "codi"
                elif any(kw in domain_lower for kw in ["research", "paper", "study", "analysis"]):
                    domain = "research"
                elif any(kw in domain_lower for kw in ["creative", "write", "story", "design"]):
                    domain = "creative"

            # Persist DPO dataset
            if dpo_all_pairs:
                try:
                    dpo_harvester.save_preference_dataset(dpo_all_pairs, f"{domain}_dpo")
                except Exception as e:
                    logger.warning(f"[ DREAMING CYCLE ] Failed to persist DPO dataset: {e}")

            forge = LoRAForge(settings=getattr(services, "settings", None))
            await forge.forge_knowledge(domain, new_data, historical_data)

            # ═══════════════════════════════════════════════════════════════
            # STEP 5: MEMORY DISTILLATION & CONSOLIDATION SWEEP
            # ═══════════════════════════════════════════════════════════════
            logger.info("[ DREAMING CYCLE ] Step 5/5: Executing H-LSM consolidation sweep and Markov Trace recalculation...")
            try:
                sweep_results = await hlsm.consolidation_sweep()
                logger.info(f"[ DREAMING CYCLE ] H-LSM Consolidation complete: {sweep_results}")
            except Exception as e:
                logger.warning(f"[ DREAMING CYCLE ] H-LSM consolidation sweep warning: {e}")

            logger.info(
                f"[ DREAMING CYCLE ] Complete. Domain={domain}, "
                f"Synthesized={len(synthetic_pairs)}, Verified={len(verified_pairs)}, "
                f"Rejected={rejected_count}, DPO_Pairs={len(dpo_all_pairs)}, "
                f"Forged={len(new_data)}+{len(historical_data)} pairs."
            )

        except ImportError as e:
            logger.warning(f"[ DREAMING CYCLE ] LoRA Forge or dependency missing: {e}")
        except Exception as e:
            logger.error(f"[ DREAMING CYCLE ] Execution failed: {e}", exc_info=True)

    # ── Job Evaluation ────────────────────────────────────────────────────

    async def _evaluate_jobs(self):
        """Check all enabled jobs and run any that are due."""
        from .models import CronJob

        with Session(self.db_engine) as session:
            stmt = select(CronJob).where(CronJob.enabled == True)  # noqa: E712
            jobs = session.exec(stmt).all()

        now = datetime.now(timezone.utc)

        for job in jobs:
            if self._is_due(job, now):
                await self._execute_job(job, now)

    def _is_due(self, job, now: datetime) -> bool:
        """Determine if a job should run at the current tick."""

        if job.schedule_type == ScheduleType.INTERVAL:
            if job.last_run_at is None:
                return True
            # schedule_value is expected to be minutes for interval
            try:
                interval_minutes = int(job.schedule_value)
            except (ValueError, TypeError):
                return False
            delta = timedelta(minutes=interval_minutes)
            return (now - job.last_run_at) >= delta

        elif job.schedule_type == ScheduleType.CRON:
            try:
                from croniter import croniter  # type: ignore
                start_time = job.last_run_at or (now - timedelta(days=1))
                if now.tzinfo is not None and start_time.tzinfo is None:
                    start_time = start_time.replace(tzinfo=now.tzinfo)
                elif now.tzinfo is None and start_time.tzinfo is not None:
                    start_time = start_time.replace(tzinfo=None)
                
                cron = croniter(job.schedule_value, start_time)
                next_run = cron.get_next(datetime)
                if next_run.tzinfo is None and now.tzinfo is not None:
                    next_run = next_run.replace(tzinfo=now.tzinfo)
                return now >= next_run
            except ImportError:
                logger.warning("[CronEngine] croniter not installed, skipping cron-type jobs")
                return False
            except Exception as e:
                logger.error(f"[CronEngine] Cron parse error for job {job.id}: {e}")
                return False

        elif job.schedule_type == ScheduleType.RUN_AT:
            if job.last_run_at is not None:
                return False  # one-shot already fired
            try:
                target = datetime.fromisoformat(job.schedule_value)
                if target.tzinfo is None:
                    target = target.replace(tzinfo=timezone.utc)
                return now >= target
            except Exception:
                return False

        return False

    # ── Execution ─────────────────────────────────────────────────────────

    async def _execute_job(self, job, now: datetime):
        """Execute a single cron job and record the run."""
        from .models import CronRun

        logger.info(f"[CronEngine] Executing job: {job.name} (id={job.id})")
        started_at = datetime.now(timezone.utc)
        status = "ok"
        log_text = ""
        delivery_status = "none"

        try:
            # --- TASK INTEGRATION ---
            # Create a Task record so it appears in the Task Manager
            if self.task_manager:
                from .models import TaskUpdate, TaskPriority
                task_desc = f"[CRON] {job.name}: {job.payload or 'Execute scheduled task'}"
                # Map thinking level or some other attribute to priority if needed, but default to MEDIUM
                await self.task_manager.add_task(TaskUpdate(
                    description=task_desc,
                    completed=False,
                    priority=TaskPriority.MEDIUM
                ), agent_id=job.agent_id)

            if self.orchestrator:
                # Build the objective from the job's payload
                objective = f"[CRON JOB: {job.name}] {job.payload or 'Execute scheduled task'}"

                # Apply model overrides
                overrides = {}
                if job.model_override:
                    overrides["model"] = job.model_override
                if job.thinking_level:
                    overrides["thinking_level"] = job.thinking_level

                result = await self.orchestrator.execute_objective(
                    objective=objective,
                    autonomy="RESTRICTED",
                )
                log_text = str(result)[:4000]  # Cap log length
            else:
                log_text = "No orchestrator connected"
                status = "skipped"

        except Exception as e:
            status = "error"
            log_text = f"{type(e).__name__}: {e}"
            logger.error(f"[CronEngine] Job {job.id} failed: {e}")

        finished_at = datetime.now(timezone.utc)

        # Delivery routing
        if status == "ok" and job.delivery_mode and job.delivery_mode != DeliveryMode.NONE:
            delivery_status = await self._deliver(job, log_text)

        # Record run history
        run = CronRun(
            job_id=job.id,
            started_at=started_at,
            finished_at=finished_at,
            status=status,
            delivery_status=delivery_status,
            log_text=log_text,
        )

        with Session(self.db_engine) as session:
            session.add(run)
            # Update last_run_at on the job
            db_job = session.get(type(job), job.id)
            if db_job:
                db_job.last_run_at = now
                session.add(db_job)
            session.commit()

        logger.info(f"[CronEngine] Job {job.id} completed: {status}")

    async def _deliver(self, job, content: str) -> str:
        """Route job output to the configured channel adapter (Sovereign Spec §3.2)."""
        if not job.delivery_channel or not self.channel_registry:
            return "no_channel"

        adapter = self.channel_registry.get(job.delivery_channel)
        if not adapter:
            return "adapter_not_found"

        try:
            recipient = job.delivery_to or ""
            # Prepare extra routing context
            kwargs = {}
            if job.delivery_account_id:
                kwargs["account"] = job.delivery_account_id

            if job.delivery_mode == DeliveryMode.ANNOUNCE_SUMMARY:
                # Truncate for summary
                summary = content[:500] + ("..." if len(content) > 500 else "")
                await adapter.send(recipient, f"📋 Cron Job '{job.name}' completed:\n{summary}", **kwargs)
            elif job.delivery_mode == DeliveryMode.POST_TRANSCRIPT:
                await adapter.send(recipient, f"📜 Full transcript for '{job.name}':\n{content}", **kwargs)
            
            return "delivered"
        except Exception as e:
            logger.error(f"[CronEngine] Delivery failed for job {job.id}: {e}")
            return f"error: {e}"

    # ── CRUD Helpers (called from FastAPI routes) ─────────────────────────

    def list_jobs(self, agent_id: str = "executive") -> List[Dict[str, Any]]:
        from .models import CronJob
        with Session(self.db_engine) as session:
            jobs = session.exec(select(CronJob).where(CronJob.agent_id == agent_id)).all()
            return [self._job_to_dict(j) for j in jobs]

    def get_job(self, job_id: int, agent_id: str = "executive") -> Optional[Dict[str, Any]]:
        from .models import CronJob
        with Session(self.db_engine) as session:
            job = session.get(CronJob, job_id)
            if job and job.agent_id == agent_id:
                return self._job_to_dict(job)
            return None

    def create_job(self, data: Dict[str, Any]) -> Dict[str, Any]:
        from .models import CronJob
        job = CronJob(**data)
        with Session(self.db_engine) as session:
            session.add(job)
            session.commit()
            session.refresh(job)
            return self._job_to_dict(job)

    def update_job(self, job_id: int, data: Dict[str, Any], agent_id: str = "executive") -> Optional[Dict[str, Any]]:
        from .models import CronJob
        with Session(self.db_engine) as session:
            job = session.get(CronJob, job_id)
            if not job or job.agent_id != agent_id:
                return None
            for k, v in data.items():
                if hasattr(job, k):
                    setattr(job, k, v)
            session.add(job)
            session.commit()
            session.refresh(job)
            return self._job_to_dict(job)

    def delete_job(self, job_id: int, agent_id: str = "executive") -> bool:
        from .models import CronJob
        with Session(self.db_engine) as session:
            job = session.get(CronJob, job_id)
            if not job or job.agent_id != agent_id:
                return False
            session.delete(job)
            session.commit()
            return True

    def clone_job(self, job_id: int, agent_id: str = "executive") -> Optional[Dict[str, Any]]:
        from .models import CronJob
        with Session(self.db_engine) as session:
            original = session.get(CronJob, job_id)
            if not original or original.agent_id != agent_id:
                return None
            clone = CronJob(
                name=f"{original.name} (copy)",
                schedule_type=original.schedule_type,
                schedule_value=original.schedule_value,
                payload=original.payload,
                model_override=original.model_override,
                thinking_level=original.thinking_level,
                delivery_channel=original.delivery_channel,
                delivery_account_id=original.delivery_account_id,
                delivery_to=original.delivery_to,
                delivery_mode=original.delivery_mode,
                reset_context=original.reset_context,
                enabled=False,  # cloned jobs start disabled
            )
            session.add(clone)
            session.commit()
            session.refresh(clone)
            return self._job_to_dict(clone)

    def force_run(self, job_id: int, agent_id: str = "executive") -> Optional[Dict[str, Any]]:
        """Schedule an immediate run regardless of schedule."""
        from .models import CronJob
        with Session(self.db_engine) as session:
            job = session.get(CronJob, job_id)
            if not job or job.agent_id != agent_id:
                return None
        asyncio.create_task(self._execute_job(job, datetime.now(timezone.utc)))
        return {"status": "triggered", "job_id": job_id}

    def get_runs(
        self,
        job_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        from .models import CronRun
        with Session(self.db_engine) as session:
            stmt = select(CronRun).order_by(col(CronRun.started_at).desc())
            if job_id:
                stmt = stmt.where(CronRun.job_id == job_id)
            if status:
                stmt = stmt.where(CronRun.status == status)
            stmt = stmt.limit(limit)
            runs = session.exec(stmt).all()
            return [self._run_to_dict(r) for r in runs]

    # ── Serialization ─────────────────────────────────────────────────────

    @staticmethod
    def _job_to_dict(job) -> Dict[str, Any]:
        return {
            "id": job.id,
            "name": job.name,
            "schedule_type": job.schedule_type,
            "schedule_value": job.schedule_value,
            "payload": job.payload,
            "model_override": job.model_override,
            "thinking_level": job.thinking_level,
            "delivery_channel": job.delivery_channel,
            "delivery_account_id": job.delivery_account_id,
            "delivery_to": job.delivery_to,
            "delivery_mode": job.delivery_mode,
            "reset_context": job.reset_context,
            "enabled": job.enabled,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "last_run_at": job.last_run_at.isoformat() if job.last_run_at else None,
        }

    @staticmethod
    def _run_to_dict(run) -> Dict[str, Any]:
        return {
            "id": run.id,
            "job_id": run.job_id,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "status": run.status,
            "delivery_status": run.delivery_status,
            "log_text": run.log_text,
        }
