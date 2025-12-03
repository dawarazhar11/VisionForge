"""
AssemblyProject model - Stores uploaded 3D assembly files and metadata.
"""
from sqlalchemy import Column, String, DECIMAL, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from datetime import datetime

from app.database import Base


class AssemblyProject(Base):
    """3D assembly project model."""

    __tablename__ = "assembly_projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name = Column(String(255), nullable=False)
    description = Column(Text)
    file_path = Column(String(500), nullable=False)
    file_size_mb = Column(DECIMAL(10, 2), nullable=False)
    file_type = Column(String(50), nullable=False)  # blend, obj, stl, fbx
    status = Column(String(50), default="uploaded", index=True)
    metadata_json = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="projects")
    jobs = relationship(
        "TrainingJob",
        back_populates="project",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<AssemblyProject(id={self.id}, name={self.name}, status={self.status})>"
