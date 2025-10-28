from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os

from app.database import get_db
from app.models import User
from app.crud import task as task_crud
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/images", tags=["images"])

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")


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
    
    # Verify this filename matches the task's preview
    if not task.preview_local_path or filename not in task.preview_local_path:
        raise HTTPException(status_code=403, detail="Invalid preview file")
    
    if not os.path.exists(task.preview_local_path):
        raise HTTPException(status_code=404, detail="Preview image not found")
    
    return FileResponse(task.preview_local_path)


@router.get("/output/{task_id}/{filename}")
async def get_output_image(
    task_id: str,
    filename: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    raise NotImplementedError("Output image is not implemented yet")