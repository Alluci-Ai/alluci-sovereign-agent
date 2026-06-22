# -*- coding: utf-8 -*-
"""
Copyright © 2026 Alluci-Ai. All Rights Reserved.
Subagent Core Lifecycle Component - Injects autonomous registration routines.
"""

import asyncio
import logging
from backend.auth.autonomous_discoverer import AlluciAutonomousDiscoverer

logger = logging.getLogger("SubagentBoot")

class AlluciSubagentRuntime:
    def __init__(self, subagent_id: str, secure_manifest: str):
        self.subagent_id = subagent_id
        # Instantiate the onboarding mechanism directly into the subagent core parameters
        self.authenticator = AlluciAutonomousDiscoverer(
            manifest_path=secure_manifest
        )
        self.active_credentials = {}  # type: ignore

    async def bind_to_target_resource(self, service_url: str):
        """Prepares the subagent to run tasks by registering with external endpoints."""
        logger.info(f"[SUBAGENT {self.subagent_id}] Mapping environment vectors to target: {service_url}")
        
        registration_details = await self.authenticator.discover_and_register(service_url)
        
        if registration_details and "api_key" in registration_details:
            # Save the returned access credentials safely inside volatile system memory
            self.active_credentials[service_url] = registration_details["api_key"]
            logger.info(f"[SUBAGENT {self.subagent_id}] Credentials verified and cached. Active task loop authorized.")
        else:
            logger.warning(f"[SUBAGENT {self.subagent_id}] Autonomous onboarding paused. User confirmation required.")

async def test_boot_sequence():
    # For testing, ensure vault is mock-initialized if necessary, 
    # but actual production will have the main orchestrator initialized.
    agent = AlluciSubagentRuntime(subagent_id="ScraperAgent-09", secure_manifest="./backend/config/skill_manifest.json")
    await agent.bind_to_target_resource("http://localhost:8000")

if __name__ == "__main__":
    asyncio.run(test_boot_sequence())
