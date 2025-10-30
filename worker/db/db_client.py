# db client to update the database

## use crud defined in app/crud/task.py

from app.schemas import ProcessingTaskUpdate
from app.models import TaskStatus
from datetime import datetime
from app.crud import task as task_crud
from app.database import get_db
from app.logger_config import get_logger

logger = get_logger(__name__)

class DBClient:
    '''
    DB client to update the database
    '''
    def __init__(self):
        # self.db = get_db()
        pass

    async def update_task_status(self, task_id, changed_fields: dict):
        '''
        Update the task status in the database
        '''
        db = next(get_db())
        try:
            # TODO: should add validation for changed_fields
            task_update = ProcessingTaskUpdate()
            if 'todb_status' in changed_fields:
                task_update.status = TaskStatus(changed_fields['todb_status'].upper())

            # preview_local_path and output_image_s3_key removed - paths are now inferred from input_image_s3_ke
            if changed_fields['todb_status'] == 'COMPLETED':
                task_update.completed_at = datetime.now()
                
            task_crud.update_task(db, task_id, task_update)
        finally:
            db.close()