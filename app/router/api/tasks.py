from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from uuid import UUID
from app.models import User, TaskStatus
from typing import Optional, List
import os
import uuid
import aiofiles
import asyncio
import json

from app.database import get_db
from app.schemas import ProcessingTaskCreate, ProcessingTask, ProcessingTaskUpdate
from app.crud import task as task_crud
from app.core.dependencies import get_strict_rate_limiter, get_moderate_rate_limiter, get_current_user, get_current_user_from_query
from app.logger_config import get_logger
from app.core.queue import BaseTaskQueueService, QueueTaskPayload
from app.core.dependencies import get_queue_service
from app.core.redis import RedisClient

logger = get_logger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_FILE_SIZE = 10 * 1024 * 1024


@router.post("/create", response_model=ProcessingTask, status_code=status.HTTP_201_CREATED, dependencies=[get_strict_rate_limiter()])
async def create_task(
    file: UploadFile = File(...),
    task_type: str = Form(...),
    parameters: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    task_queue: BaseTaskQueueService = Depends(get_queue_service)  # Inject here
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    try:
        # step 1: validate file and store it locally
        content = await file.read()
        
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400, 
                detail=f"File too large. Max size: {MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        file_id = str(uuid.uuid4())
        file_name = f"{file_id}{file_ext}"
        file_path = file_name
        
        async with aiofiles.open(os.path.join(os.path.expanduser(os.getenv("ROOT_DIR")), os.getenv("UPLOAD_DIR"), file_path), 'wb') as f:
            await f.write(content)
        
        logger.info(f"File uploaded: {file_name} by user {current_user.email}")
        
        
        if parameters:
            try:
                params_dict = json.loads(parameters)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid parameters format, must be valid JSON")
        else:
            params_dict = None
        # step 2: store file in S3
        # TODO: implement S3 storage
        # considering not upload to S3 immediately, maybe later when local worker is processing the preview results

        task_id = uuid.uuid4()
        # step 3: enqueue task to Redis queue
        task_payload = QueueTaskPayload(
            task_id=task_id,
            task_type=task_type,
            user_id=current_user.id,
            input_image_s3_key=file_name,
            input_image_local_path=file_path,
            parameters=params_dict
        )

        await task_queue.enqueue(task_payload)

        # step 4: create task in postgres db
        task_in = ProcessingTaskCreate(
            id=task_id,
            task_type=task_type,
            input_image_s3_key=file_name,
            parameters=params_dict
        )
        task = task_crud.create_task(
            db, 
            user_id=current_user.id, 
            task=task_in, 
            model_version="v1.0"
        )
        logger.info(f"Task created: {task.id} for user {current_user.email}")
        return task
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Task creation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Task creation failed")


# get task by user id
@router.get("/all-tasks", response_model=List[ProcessingTask], status_code=status.HTTP_200_OK, dependencies=[get_strict_rate_limiter()])
async def get_tasks_by_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        logger.info(f"get_tasks_by_user: user_id: {current_user.id}")
        tasks = task_crud.get_tasks_by_user(db, user_id=current_user.id)
        if tasks is None or len(tasks) == 0:
            raise HTTPException(status_code=404, detail="No tasks found")
        logger.info(f"get_tasks_by_user: user_id: {current_user.id}, task count: {len(tasks)}")
        return tasks
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_tasks_by_user failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))




# get task by task id
@router.get("/{task_id}", response_model=ProcessingTask, status_code=status.HTTP_200_OK, dependencies=[get_strict_rate_limiter()])
async def get_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = task_crud.get_task(db, task_id)
    if task is None or task.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

def generate_preview_url(task_id: UUID, filename: str):
    return f"/api/images/preview/{task_id}/{filename}"

def generate_output_url(task_id: UUID, filename: str):
    # return f"/api/images/output/{task_id}/{filename}"
    raise NotImplementedError("Not implemented")

# use Redis Pub/Sub to mobnitor task progress
# use Server-Sent Events (SSE) to stream task progress
@router.get("/{task_id}/stream", dependencies=[get_strict_rate_limiter()])
async def stream_task_status(
    task_id: UUID,
    current_user: User = Depends(get_current_user_from_query),
    db: Session = Depends(get_db)
):
    # Verify task ownership
    task = task_crud.get_task(db, task_id)
    if not task or task.user_id != current_user.id:
        async def error_generator():
            yield f"data: {json.dumps({'error': 'Task not found'})}\n\n"
        return StreamingResponse(error_generator(), media_type="text/event-stream")
    

    async def event_generator():
        try:
            # Get Redis client
            redis_client = await RedisClient.get_client(db=int(os.getenv("REDIS_QUEUE_DB", 0)))
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(f"task:{str(task_id)}")
            
            # frontend expected keys: status, preview_ready, preview_url, output_ready, output_url
            # statusL COMPLETED, FAILED, PROCESSING, PENDING

            # Send initial state immediately
            initial_data = {
                'status': 'PENDING',
                'preview_ready': False,
                'preview_url': None,
                'output_ready': False,
                'output_url': None,
            }
            logger.info(f"task_id: {str(task_id)}, stream_task_status: initial_data: {initial_data}")
            yield f"data: {json.dumps(initial_data)}\n\n"
            
            # Listen for updates
            response_data = {}
            async for message in pubsub.listen():  # data is a JSON string, keys: status, preview_local_path, final_output_path
                if message['type'] == 'message':
                    message_data = json.loads(message['data'])
                    if message_data['status'] == 'COMPLETED':
                        response_data['status'] = 'COMPLETED'
                        response_data['preview_ready'] = True
                        response_data['preview_url'] = generate_preview_url(task_id, message_data['preview_local_path'])
                        response_data['output_ready'] = True
                        response_data['output_url'] = generate_output_url(task_id, message_data['final_output_path'])
                    
                    elif message_data['status'] == 'PROCESSING':
                        response_data['status'] = 'PROCESSING'
                        response_data['preview_ready'] = True
                        response_data['preview_url'] = generate_preview_url(task_id, message_data['preview_local_path'])

                    elif message_data['status'] == 'FAILED':
                        response_data['status'] = 'FAILED'


                    logger.info(f"task_id: {str(task_id)}, recieve redis pub/sub message, stream_task_status: message from redis: {message}. response_data: {response_data}")
                    yield f"data: {json.dumps(response_data)}\n\n"

                    if response_data.get('status') in ['COMPLETED', 'FAILED']:
                        await pubsub.unsubscribe()
                        break

        except Exception as e:
            logger.error(f"SSE stream error for task {task_id}: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
