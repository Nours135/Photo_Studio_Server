from __future__ import annotations  # for type hints
import asyncio
from typing import Dict, Type, Any, List
from collections import defaultdict
from datetime import datetime
from worker.db.queue_client import QueueClient
from worker.models.base import BaseModel
from app.logger_config import get_logger
from app.core.queue import QueueTaskPayload


logger = get_logger(__name__)


class ModelOrchestrator:
    """
    Central manager for all models, handles task dispatching and statistics
    """
    def __init__(self):
        self._queue_client = QueueClient()
        self.models: Dict[str, BaseModel] = {}  # name to instance 
        self.model_classes: Dict[str, Type[BaseModel]] = {}   # name to class
        self._running = False
        self._background_tasks = []
        
        # Statistics
        # self.stats = dict()  # model class name to stats
        # stats stored in lower level model wrapper class: BaseModel
    
    def register_model(self, model_type: str, model_class: Type[BaseModel]):
        '''
        Register a model class for lazy initialization
        '''
        self.model_classes[model_type] = model_class
        logger.info(f"Registered model type: {model_type}")


    async def _get_or_create_model(self, model_type: str) -> BaseModel:
        '''
        Lazy load models only when needed
        '''
        if model_type not in self.models: 
            if model_type not in self.model_classes:
                raise ValueError(f"Unknown model type: {model_type}")
            
            logger.info(f"Initializing model: {model_type}")
            model = self.model_classes[model_type]()  # call model's init method to create instance
            self.models[model_type] = model
            
            # Start idle detection for this model (non-blocking)
            task = asyncio.create_task(model.start_idle_detection())
            self._background_tasks.append(task)
        
        return self.models[model_type]


    async def _process_task(self, task: QueueTaskPayload):
        '''
        Process a single task
        '''
        model_type = task.task_type  # task type is the model type        
        try:
            model = await self._get_or_create_model(model_type)
            result = await model.predict_async(task)
            return result
            
        except Exception as e:
            logger.error(f"Task processing error: {e}", exc_info=True)
            raise

    async def run(self, max_concurrent_tasks: int = 5):
        """
        Main loop: fetch tasks from Redis and dispatch to workers
        Uses semaphore to limit concurrent tasks
        """
        self._running = True
        semaphore = asyncio.Semaphore(max_concurrent_tasks)
        active_tasks = set()
        
        logger.info(f"Orchestrator started with max {max_concurrent_tasks} concurrent tasks")
        
        try:
            while self._running:
                try:
                    # Non-blocking task fetch with timeout
                    task = await self._queue_client.get_task()  # already deal with timeout in queue client
                    
                    if task:  # if no task, return None, do not need to deal with blocking and timeout here
                        # Process task without blocking
                        async def process_with_semaphore(t):
                            async with semaphore:
                                try:
                                    await self._process_task(t) 
                                except Exception as e:
                                    logger.error(f"Task failed: {e}", exc_info=True)
                        
                        task_coro = asyncio.create_task(process_with_semaphore(task))
                        active_tasks.add(task_coro)
                        task_coro.add_done_callback(active_tasks.discard)
                        
                except Exception as e:
                    logger.error(f"Error fetching task: {e}", exc_info=True)
                    await asyncio.sleep(60.0)  # 1 minute timeout

            if not self._running:
                await self.shutdown(active_tasks)
                    
        except KeyboardInterrupt:
            logger.info("Shutdown requested")
        finally:
            await self.shutdown(active_tasks)
    

    async def shutdown(self, active_tasks: set = None):
        '''
        Graceful shutdown, 
        '''
        logger.info("Shutting down orchestrator...")
        self._running = False
        
        # Wait for active tasks to complete
        if active_tasks:
            logger.info(f"Waiting for {len(active_tasks)} active tasks to complete...")
            await asyncio.gather(*active_tasks, return_exceptions=True)
        
        # Cancel idle detection tasks
        for task in self._background_tasks:
            task.cancel()
        await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        # Unload all models
        for model_type, model in list(self.models.items()):
            logger.info(f"Unloading model: {model_type}")
            await model.stop()
        
        logger.info("Orchestrator shutdown complete")
    

    def get_model_stats(self) -> Dict[str, Dict[str, Any]]:
        '''
        Get statistics of all models
        '''
        return {model_type: model.stats for model_type, model in self.models.items()}



    # TODO: add redis alert for task completion and failure