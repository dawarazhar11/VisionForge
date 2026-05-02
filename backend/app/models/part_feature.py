"""
PartFeature model - Manufacturing features extracted from a STEP file.

Each row represents one detected feature (hole, boss, fillet, etc.)
with its 3D coordinates and dimensions. These records drive both
automatic YOLO annotation generation and real-part detection mapping.
"""
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from datetime import datetime

from app.database import Base


FEATURE_CLASS_ORDER = [
    "hole",
    "threaded_hole",
    "boss",
    "slot",
    "pocket",
    "chamfer",
    "fillet",
    "planar_face",
]


class PartFeature(Base):
    """Single manufacturing feature recognised from a STEP file."""

    __tablename__ = "part_features"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("assembly_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Feature classification
    feature_type = Column(String(50), nullable=False, index=True)
    class_index = Column(Integer, nullable=False)

    # 3D centroid (world-space, same units as the STEP file)
    center_x = Column(Float, nullable=False)
    center_y = Column(Float, nullable=False)
    center_z = Column(Float, nullable=False)

    # Axis / surface normal (unit vector)
    normal_x = Column(Float, nullable=False, default=0.0)
    normal_y = Column(Float, nullable=False, default=0.0)
    normal_z = Column(Float, nullable=False, default=1.0)

    # Dimensions (nullable — not all apply to every feature type)
    radius = Column(Float, nullable=True)   # holes, bosses, fillets
    depth  = Column(Float, nullable=True)   # holes, pockets
    width  = Column(Float, nullable=True)   # slots
    length = Column(Float, nullable=True)   # slots

    # Feature-specific extras (area, is_through_hole, pitch, etc.)
    properties_json = Column(JSONB, default={})

    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("AssemblyProject", back_populates="features")

    def __repr__(self):
        return (
            f"<PartFeature(type={self.feature_type}, class={self.class_index}, "
            f"center=({self.center_x:.2f},{self.center_y:.2f},{self.center_z:.2f}))>"
        )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "feature_type": self.feature_type,
            "class_index": self.class_index,
            "center": [self.center_x, self.center_y, self.center_z],
            "normal": [self.normal_x, self.normal_y, self.normal_z],
            "radius": self.radius,
            "depth": self.depth,
            "width": self.width,
            "length": self.length,
            "properties": self.properties_json or {},
        }
