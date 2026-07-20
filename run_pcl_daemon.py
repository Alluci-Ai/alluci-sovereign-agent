import asyncio
import logging
from backend.pcl import ProactiveCognitionLoop
import backend.services as services

logging.basicConfig(level=logging.INFO, format="[SOVEREIGN DAEMON] %(asctime)s - %(levelname)s - %(message)s")



async def main():
    logging.info("Initializing Alluci Sovereign Agent Workspace...")
    
    class MockApp:
        pass
    
    await services.init_services(MockApp())
    
    orchestrator = services.orchestrator
    
    # 1. Initialize the 3-Pillar Action Verification Loop (AVL) Gate is natively handled by the Orchestrator now!
    if orchestrator is not None:
        orchestrator.max_healing_attempts = 3
    
    # 3. Spin up the 5-Stage Proactive Cognition Loop (30-second cycle)
    # The PCL is already initialized by init_services, so we just update the interval
    if services.pcl:
        services.pcl.cycle_interval = 30.0
    
    # 4. Bind to active background loop execution
    logging.info("Starting background surveillance matrices. Press Ctrl+C to isolate agent.")
    
    # Keep the event loop alive forever since PCL runs as an asyncio Task internally
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.critical("Sovereign Agent core gracefully detached from local workspace.")
