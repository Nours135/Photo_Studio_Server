from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from app.models import User

from app.database import get_db
from app.schemas import ProcessingTaskCreate, ProcessingTask, ProcessingTaskUpdate
from app.crud import task as task_crud
from app.core.dependencies import get_strict_rate_limiter, get_moderate_rate_limiter, get_current_user

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=ProcessingTask, status_code=status.HTTP_201_CREATED, dependencies=[get_strict_rate_limiter()])
def create_task(
    task_in: ProcessingTaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = task_crud.create_task(db, user_id=current_user.id, task=task_in, model_version="v1.0")
    return task


@router.patch("/{task_id}", response_model=ProcessingTask, dependencies=[get_moderate_rate_limiter()])
def update_task(
    task_id: UUID,
    task_update: ProcessingTaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    updated_task = task_crud.update_task(db, task_id, task_update)
    
    if not updated_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    if updated_task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this task"
        )
    
    return updated_task
