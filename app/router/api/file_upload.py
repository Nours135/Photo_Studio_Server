from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from app.logger_config import get_logger
from app.core.dependencies import get_current_user, get_strict_rate_limiter
from app.models import User
import os
import uuid
import aiofiles

logger = get_logger(__name__)

router = APIRouter(prefix="/upload", tags=["upload"])

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_FILE_SIZE = 10 * 1024 * 1024


@router.post("", dependencies=[get_strict_rate_limiter()])
async def upload_file(
    file: UploadFile = File(..., max_length=MAX_FILE_SIZE),   # restrict file size
    current_user: User = Depends(get_current_user)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    file_id = str(uuid.uuid4())
    file_name = f"{file_id}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, file_name)
    
    try:
        content = await file.read()
        
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400, 
                detail=f"File too large. Max size: {MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        logger.info(f"File uploaded: {file_name} by user {current_user.email}")
        
        return {
            "message": "File uploaded successfully",
            "file_id": file_id,
            "file_path": file_name,
            "original_filename": file.filename
        }
    
    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail="File upload failed")
