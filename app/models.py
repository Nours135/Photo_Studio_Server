from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import enum
import uuid

Base = declarative_base()


class SubscriptionTier(str, enum.Enum):
    FREE = "FREE"
    PRO = "PRO"


class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100))
    password_hash = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True))
    subscription_tier = Column(
        SQLEnum(SubscriptionTier, name="subscription_tier_type"),
        default=SubscriptionTier.FREE,
        nullable=False
    )


class ProcessingTask(Base):
    __tablename__ = "processing_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    task_type = Column(String(50), nullable=False, index=True)
    status = Column(
        SQLEnum(TaskStatus, name="task_status_type"),
        nullable=False,
        index=True
    )
    
    input_image_s3_key = Column(Text, nullable=False)
    output_image_s3_key = Column(Text)
    
    parameters = Column(JSONB)
    
    processing_time_ms = Column(Integer)
    model_version = Column(String(50))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    completed_at = Column(DateTime(timezone=True))

