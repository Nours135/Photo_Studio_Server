from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from app.models import SubscriptionTier, TaskStatus


class UserBase(BaseModel):
    email: EmailStr
    username: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class User(UserBase):
    id: UUID
    created_at: datetime
    last_login: Optional[datetime] = None
    subscription_tier: SubscriptionTier
    
    model_config = ConfigDict(from_attributes=True)


class ProcessingTaskBase(BaseModel):
    task_type: str
    parameters: Optional[Dict[str, Any]] = None


class ProcessingTaskCreate(ProcessingTaskBase):
    id: UUID
    input_image_s3_key: str


class ProcessingTaskUpdate(BaseModel):
    status: Optional[TaskStatus] = None
    processing_time_ms: Optional[int] = None
    completed_at: Optional[datetime] = None


class ProcessingTask(ProcessingTaskBase):
    id: UUID
    user_id: UUID
    status: TaskStatus
    input_image_s3_key: str  # All paths inferred from this
    processing_time_ms: Optional[int] = None
    model_version: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
