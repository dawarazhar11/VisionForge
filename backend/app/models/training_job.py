"""
TrainingJob model - Tracks synthetic data generation and model training jobs.
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from datetime import datetime

from app.database import Base


class TrainingJob(Base):
    """Model training job tracking."""

    __tablename__ = "training_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("assembly_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    status = Column(String(50), default="pending", index=True)
    progress = Column(Integer, default=0)  # 0-100%
    stage = Column(String(100))  # rendering, training, converting, etc.
    config_json = Column(JSONB, nullable=False)
    dataset_path = Column(String(500))
    metrics_json = Column(JSONB)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Relationships
    project = relationship("AssemblyProject", back_populates="jobs")
    models = relationship(
        "Model",
        back_populates="job",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<TrainingJob(id={self.id}, status={self.status}, progress={self.progress}%)>"
