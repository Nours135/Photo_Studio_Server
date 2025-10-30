from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
import os

from app.database import get_db
from app.models import User
from app.crud import task as task_crud
from app.core.dependencies import get_current_user, get_storage_service, get_s3_storage_service
from app.logger_config import get_logger
from app.core.storage import StorageService



logger = get_logger(__name__)

router = APIRouter(prefix="/images", tags=["images"])

@router.get("/preview/{task_id}/{filename}")
async def get_preview_image(
    task_id: str,
    filename: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage_service: StorageService = Depends(get_storage_service)
):
    logger.info(f"get_preview_image: task_id: {task_id}, filename: {filename}")
    # Security: prevent path traversal
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    # Verify task ownership
    # import pdb; pdb.set_trace()
    task = task_crud.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.user_id != current_user.id or filename != task.input_image_s3_key:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Infer preview/output filename from input_image_s3_key
    expected_preview_id = StorageService.get_output_id(task.input_image_s3_key)
    preview_content = await storage_service.read(expected_preview_id)
    # logger.info(f"get_preview_image: preview_content: {len(preview_content)} bytes")

    if not preview_content:
        raise HTTPException(status_code=404, detail="Preview image not found")
    
    return Response(content=preview_content, media_type="image/png")

@router.get("/output/{task_id}/{filename}")
async def get_output_image(
    task_id: str,
    filename: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage_service: StorageService = Depends(get_s3_storage_service)
):
    logger.info(f"get_output_image: task_id: {task_id}, filename: {filename}")

    # Security: prevent path traversal
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Verify task ownership
    task = task_crud.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.user_id != current_user.id or filename != task.input_image_s3_key:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Infer output filename from input_image_s3_key
    output_id = StorageService.get_output_id(task.input_image_s3_key)
    
    output_content = await storage_service.read(output_id)
    # logger.info(f"get_output_image: output_content: {len(output_content)} bytes")
    if not output_content:
        raise HTTPException(status_code=404, detail="Output image not found")
    
    return Response(content=output_content, media_type="image/png")


