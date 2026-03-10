
import asyncio
import os
import json
import logging
import hashlib
import re
from datetime import datetime, time, timezone
from typing import List, Dict, Any, Optional
from .security.vault import VaultManager

class Probe:
    """Base class for deterministic checks."""
    def __init__(self, context: str):
        self.context = context

    async def check(self) -> Optional[Dict[str, Any]]:
        """Subclasses must implement this to perform deterministic checks."""
        return None

class FileProbe(Probe):
    """Checks for changes in a specific directory or file."""
    def __init__(self, path: str, last_hash: str = ""):
        self.path = path
        self.last_hash = last_hash

    async def check(self) -> Optional[Dict[str, Any]]:
        if not os.path.exists(self.path):
            return None
        
        # Simple modification time check first (cheap)
        try:
            # Removed unused variable 'mtime'
            # If it's a file, hash it for accuracy
            if os.path.isfile(self.path):
                with open(self.path, "rb") as f:
                    # Use SHA-256 for file integrity checks (Autonomy Audit)
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                
                if file_hash != self.last_hash:
                    return {"type": "file_change", "path": self.path, "hash": file_hash}
        except Exception:
            pass
        return None

class TaskDeadlineProbe(Probe):
    """Parses TASKS.md for expired deadlines (autonomous follow-up)."""
    def __init__(self, path: str):
        self.path = path

    async def check(self) -> Optional[Dict[str, Any]]:
        if not os.path.exists(self.path):
            return None
            
        expired_items = []
        today = datetime.now(timezone.utc).date()
        
        try:
            with open(self.path, 'r') as f:
                lines = f.readlines()
            
            for line in lines:
                # Logic: Look for unchecked boxes "- [ ]" and a date pattern YYYY-MM-DD
                if "- [ ]" in line:
                    match = re.search(r'(\d{4}-\d{2}-\d{2})', line)
                    if match:
                        date_str = match.group(1)
                        try:
                            due_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                            if due_date < today:
                                expired_items.append(line.strip())
                        except ValueError:
                            pass
                            
            if expired_items:
                return {
                    "type": "overdue_tasks", 
                    "count": len(expired_items), 
                    "details": expired_items
                }
        except Exception:
            pass
        return None

class HeartbeatDaemon:
    def __init__(self, orchestrator, vault: VaultManager, interval_seconds: int = 900):  # Default 15 mins
        self.orchestrator = orchestrator
        self.vault = vault
        self.interval = interval_seconds
        self.logger = logging.getLogger("Heartbeat")
        self.running = False
        self.state_file = "heartbeat_state.json"
        self.ws_gateway = None
        
        # Configuration
        self.quiet_hours_start = time(22, 0)  # 10 PM UTC
        self.quiet_hours_end = time(7, 0)     # 7 AM UTC
        
        # State
        self.probe_states: Dict[str, str] = self._load_state()
        self.last_pulse = None

    def _load_state(self) -> Dict[str, str]:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_state(self):
        with open(self.state_file, 'w') as f:
            json.dump(self.probe_states, f)

    def _is_quiet_hours(self) -> bool:
        now = datetime.now(timezone.utc).time()
        if self.quiet_hours_start < self.quiet_hours_end:
            return self.quiet_hours_start <= now <= self.quiet_hours_end
        else:  # Crosses midnight
            return now >= self.quiet_hours_start or now <= self.quiet_hours_end

    async def _parse_standing_orders(self) -> List[str]:
        """
        Retrieves standing orders from the Soul Manifest (Identity Layer).
        Fallback to HEARTBEAT.md if manifest entry is missing.
        """
        orders = []
        
        # 1. Try Soul Manifest (Production Path)
        try:
            manifest_data = await self.vault.retrieve_secret("soul_manifest")
            if manifest_data and "heartbeat" in manifest_data:
                raw_orders = manifest_data["heartbeat"]
                for line in raw_orders.split('\n'):
                    if line.strip().startswith("- [x]"):
                        orders.append(line.replace("- [x]", "").strip())
                if orders:
                    return orders
        except Exception as e:
            self.logger.warning(f"Failed to read Soul Manifest for heartbeat: {e}")

        # 2. Fallback to File (Legacy Path)
        if not os.path.exists("HEARTBEAT.md"):
            return []
        
        try:
            with open("HEARTBEAT.md", 'r') as f:
                lines = f.readlines()
                for line in lines:
                    if line.strip().startswith("- [x]"):  # Only active tasks
                        orders.append(line.replace("- [x]", "").strip())
        except Exception as e:
            self.logger.error(f"Failed to read HEARTBEAT.md: {e}")
            
        return orders

    async def start(self):
        self.running = True
        self.logger.info("Heartbeat Daemon Started.")
        while self.running:
            try:
                await self.pulse()
            except Exception as e:
                self.logger.error(f"Pulse Error: {e}")
            
            # Wait for next interval
            await asyncio.sleep(self.interval)

    async def stop(self):
        self.running = False
        self.logger.info("Heartbeat Daemon Stopped.")

    async def pulse(self):
        self.last_pulse = datetime.now(timezone.utc)
        
        # 1. Quiet Hours Check
        if self._is_quiet_hours():
            self.logger.info("[PULSE] Skipped (Quiet Hours)")
            return

        self.logger.info("[PULSE] Initiating system check...")

        # Update WebSocket Heartbeat Icon (Phase 3 UX)
        if self.ws_gateway:
            asyncio.create_task(self.ws_gateway.broadcast_event('system.heartbeat', {
                "timestamp": self.last_pulse.isoformat(),
                "status": "NOMINAL",
                "uptime_ms": int((datetime.now(timezone.utc) - self.last_pulse).total_seconds() * 1000)
            }))

        # 2. Read Orders
        orders = await self._parse_standing_orders()
        if not orders:
            self.logger.info("[PULSE] No standing orders found in Soul Manifest.")
            return

        changes_detected = []
        task_file = "TASKS.md"  # Central task registry
        
        # 3. Run Probes (The "Cheap" Phase)
        
        # Probe A: File Modification
        last_hash = self.probe_states.get(task_file, "")
        file_probe = FileProbe(task_file, last_hash)
        file_result = await file_probe.check()
        
        if file_result:
            self.probe_states[task_file] = file_result['hash']
            changes_detected.append(f"File '{task_file}' has been modified.")
            self._save_state()

        # Probe B: Task Deadline Check (Autonomous Follow-up)
        if any(k in " ".join(orders).lower() for k in ["overdue", "deadline", "tasks"]):
             deadline_probe = TaskDeadlineProbe(task_file)
             deadline_result = await deadline_probe.check()
             if deadline_result:
                 count = deadline_result['count']
                 items = deadline_result['details']
                 changes_detected.append(f"ALERT: {count} overdue tasks detected in {task_file}: {items}")

        # 4. Escalation Gate — IMPLEMENTED
        if changes_detected or any("monitor" in o.lower() for o in orders):
            self.logger.info("[PULSE] Escalating to Agent Reasoning...")
            await self._trigger_proactive_event(orders, changes_detected)
        else:
            self.logger.info("[PULSE] No significant changes detected.")

    async def _trigger_proactive_event(self, orders: List[str], changes: List[str]):
        """
        Escalates detected changes to the orchestrator for autonomous reasoning.
        Constructs a synthetic objective from standing orders and probe data.
        """
        if not self.orchestrator:
            self.logger.warning("[PULSE] No orchestrator connected — skipping escalation.")
            return

        # Build the proactive objective
        context_parts = ["[HEARTBEAT SYSTEM PULSE — Proactive Autonomous Action]"]
        
        if changes:
            context_parts.append("DETECTED CHANGES:\n" + "\n".join(f"  - {c}" for c in changes))
        
        context_parts.append("STANDING ORDERS:\n" + "\n".join(f"  - {o}" for o in orders))
        context_parts.append(
            "INSTRUCTION: Based on the standing orders and detected changes above, "
            "determine if autonomous action is required. If so, execute the most relevant "
            "standing order. If no action is needed, respond with a brief status summary."
        )

        objective = "\n\n".join(context_parts)

        try:
            # Execute in RESTRICTED mode — heartbeat actions should be cautious
            result = await self.orchestrator.execute_objective(
                objective=objective,
                autonomy="RESTRICTED"
            )
            self.logger.info(f"[PULSE] Proactive action completed: {str(result)[:200]}")
        except Exception as e:
            self.logger.error(f"[PULSE] Proactive escalation failed: {e}")
