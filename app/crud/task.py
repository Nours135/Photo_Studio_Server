from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

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
        parameters=task.parameters,
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
