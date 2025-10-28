from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
from typing import List

from app.models import ProcessingTask, TaskStatus
from app.schemas import ProcessingTaskCreate, ProcessingTaskUpdate


def create_task(
    db: Session,
    user_id: UUID,
    task: ProcessingTaskCreate,
    model_version: Optional[str] = None
) -> ProcessingTask:
    db_task = ProcessingTask(
        user_id=user_id,
        task_type=task.task_type,
        status=TaskStatus.PENDING,
        input_image_s3_key=task.input_image_s3_key,
        parameters=task.parameters,  # leave it as None for now, will be implemented as a JSONB field in the future
        model_version=model_version
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


def update_task(
    db: Session,
    task_id: UUID,
    task_update: ProcessingTaskUpdate
) -> Optional[ProcessingTask]:
    db_task = db.query(ProcessingTask).filter(ProcessingTask.id == task_id).first()
    if not db_task:
        return None
    
    update_data = task_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        if hasattr(db_task, field):
            setattr(db_task, field, value)
    
    db.commit()
    db.refresh(db_task)
    return db_task


def get_task(db: Session, task_id: UUID) -> Optional[ProcessingTask]:
    return db.query(ProcessingTask).filter(ProcessingTask.id == task_id).first()

def get_tasks_by_user(db: Session, user_id: UUID) -> List[ProcessingTask]:
    return db.query(ProcessingTask).filter(ProcessingTask.user_id == user_id).order_by(ProcessingTask.created_at.desc()).all()
