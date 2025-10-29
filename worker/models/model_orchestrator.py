from __future__ import annotations  # for type hints
import asyncio
from typing import Dict, Type, Any, List
import os
import json




from worker.db.queue_client import QueueClient
from worker.db.db_client import DBClient
from worker.db.notification_client import NotificationClient
from worker.models.base import BaseModel
from app.logger_config import get_logger
from app.core.queue import QueueTaskPayload
from worker.worker_config import get_worker_config, get_output_path

logger = get_logger(__name__)

class ModelOrchestrator:
    """
    Central manager for all models, handles task dispatching and statistics
    """
    def __init__(self):
        self.config = get_worker_config()
        self._queue_client = QueueClient()
        self._notification_client = NotificationClient()
        self._db_client = DBClient()
        self.models: Dict[str, BaseModel] = {}  # name to instance 
        self.model_classes: Dict[str, Type[BaseModel]] = {}   # name to class
        self._running = False        
        self._background_tasks = []
    
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

                        logger.info(f"ModelOrchestrator: processing task: {task}")
                        task_coro = asyncio.create_task(process_with_semaphore(task))
                        active_tasks.add(task_coro)
                        task_coro.add_done_callback(lambda f: self._handle_task_completion(f, task))
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

    def _handle_task_completion(self, task_future: asyncio.Future, task: QueueTaskPayload):
        '''
        Handle the task completion:
            (1) Check if the task is successful
            (2) Notify the task completion for frontend
            (3) database update
        '''
        # Step 1: check if the task is successful
         
        if self.config['ENV'] == 'local':
            # check local path
            output_local_path = get_output_path(task.input_image_local_path)
            output_path = os.path.join(os.path.expanduser(os.getenv("ROOT_DIR")), os.getenv("UPLOAD_DIR"), output_local_path)
            logger.info(f"task_id: {task.task_id}, ModelOrchestrator: output_path: {output_path}")
            if os.path.exists(output_path): # successful
                # update database
                TASK_STATUS = 'PROCESSING'  # preview is generated, but not completed
                PREVIEW_LOCAL_PATH = output_local_path
            else:
                # update database
                TASK_STATUS = 'FAILED'
                PREVIEW_LOCAL_PATH = 'N/A'
            FINAL_OUTPUT_PATH = 'N/A'
        else:
            raise NotImplementedError("Not implemented")
            # TASK_STATUS = 'COMPLETED'
            # PREVIEW_LOCAL_PATH = output_local_path
            # FINAL_OUTPUT_PATH = 'N/A'
            # TODO: download the image from S3
            # output_path = get_output_path(task.input_image_s3_key)
            
        # Step 2: notify the task completion for frontend by redis pub/sub
        message = {
            'status': TASK_STATUS,
            'preview_local_path': PREVIEW_LOCAL_PATH,
            'final_output_path': FINAL_OUTPUT_PATH
        }
        asyncio.create_task(
            self._notification_client.notify_task_status(str(task.task_id), message=json.dumps(message))
        )  # non-blocking
        logger.info(f"task_id: {task.task_id}, ModelOrchestrator: notified task completion for frontend, message: {message}")

        
        # Step 3: update to database, necessary for frontend to show the preview
        if TASK_STATUS == 'PROCESSING':
            if self.config['ENV'] == 'local':
                updated_fields = {
                    'todb_status': 'PROCESSING',
                    'preview_local_path': PREVIEW_LOCAL_PATH
                }
            else:
                raise NotImplementedError("Not implemented")
        
            asyncio.create_task(
                self._db_client.update_task_status(task.task_id, updated_fields)
            )  # non-blocking

            logger.info(f"task_id: {task.task_id}, ModelOrchestrator: updated database, updated_fields: {updated_fields}")
        elif TASK_STATUS == 'COMPLETED':
            raise NotImplementedError("Not implemented")