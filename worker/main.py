import asyncio
from worker.models.model_orchestrator import ModelOrchestrator
from worker.models.bgrm import BackgroundRemovalModel
from app.logger_config import get_logger
from worker.worker_config import get_worker_config

logger = get_logger(__name__)
config = get_worker_config()

logger.info(f"Worker {config['ENV']} started with config: {config}")



async def main():
    orchestrator = ModelOrchestrator()
    
    # Register all model types
    orchestrator.register_model("background_removal", BackgroundRemovalModel)
    
    # Run orchestrator
    await orchestrator.run(max_concurrent_tasks=5)

if __name__ == "__main__":
    asyncio.run(main())