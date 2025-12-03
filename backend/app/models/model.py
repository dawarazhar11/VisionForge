"""
Model - Stores trained model files and metadata.
"""
from sqlalchemy import Column, String, Boolean, DECIMAL, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from datetime import datetime

from app.database import Base


class Model(Base):
    """Trained model artifact."""

    __tablename__ = "models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("training_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name = Column(String(255), nullable=False)
    format = Column(String(50), nullable=False, index=True)  # tflite, coreml, pt
    file_path = Column(String(500), nullable=False)
    file_size_mb = Column(DECIMAL(10, 2), nullable=False)
    accuracy_metrics = Column(JSONB)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    job = relationship("TrainingJob", back_populates="models")

    def __repr__(self):
        return f"<Model(id={self.id}, name={self.name}, format={self.format})>"
