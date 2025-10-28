from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from uuid import UUID
from app.models import User
from typing import Optional
import os
import uuid
import aiofiles
import json

from app.database import get_db
from app.schemas import ProcessingTaskCreate, ProcessingTask, ProcessingTaskUpdate
from app.crud import task as task_crud
from app.core.dependencies import get_strict_rate_limiter, get_moderate_rate_limiter, get_current_user
from app.logger_config import get_logger
from app.core.queue import BaseTaskQueueService, QueueTaskPayload
from app.core.dependencies import get_queue_service

logger = get_logger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_FILE_SIZE = 10 * 1024 * 1024


@router.post("/create", response_model=ProcessingTask, status_code=status.HTTP_201_CREATED, dependencies=[get_strict_rate_limiter()])
async def create_task(
    file: UploadFile = File(..., max_length=MAX_FILE_SIZE),
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
        file_path = os.path.join(UPLOAD_DIR, file_name)
        
        async with aiofiles.open(file_path, 'wb') as f:
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
        logger.error(f"Task creation failed: {str(e)}")
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail="Task creation failed")



