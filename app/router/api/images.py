from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os

from app.database import get_db
from app.models import User
from app.crud import task as task_crud
from app.core.dependencies import get_current_user
from app.logger_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/images", tags=["images"])

@router.get("/preview/{task_id}/{filename}")
async def get_preview_image(
    task_id: str,
    filename: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Security: prevent path traversal
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    # Verify task ownership
    task = task_crud.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # donot verify the filename matches the task's preview
    # Verify this filename matches the task's preview
    if not task.preview_local_path or filename not in task.preview_local_path:
        raise HTTPException(status_code=403, detail="Invalid preview file")
    
    preview_path = os.path.join(os.path.expanduser(os.getenv("ROOT_DIR")), os.getenv("UPLOAD_DIR"), task.preview_local_path)
    logger.info(f"task_id: {task_id}, get_preview_image: preview_path: {preview_path}")
    
    if not os.path.exists(preview_path):
        raise HTTPException(status_code=404, detail="Preview image not found")
    
    return FileResponse(preview_path)


@router.get("/output/{task_id}/{filename}")
async def get_output_image(
    task_id: str,
    filename: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    raise NotImplementedError("Output image is not implemented yet")