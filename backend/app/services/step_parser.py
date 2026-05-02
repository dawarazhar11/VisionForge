"""
STEP file parser and manufacturing feature recognition.

Pipeline:
  .step / .stp upload
    → load B-Rep geometry  (cadquery / OpenCASCADE)
    → analyse topology: cylindrical, planar, toroidal faces
    → classify: hole, threaded_hole, boss, fillet, chamfer, planar_face
    → extract 3D centre + axis + dimensions for every feature
    → export part as STL for Blender import
    → return ParseResult (features list + STL path + class names)

Feature type → YOLO class mapping is deterministic and stored in
FEATURE_CLASS_ORDER so the same part always produces the same class indices.
"""

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from loguru import logger

try:
    import cadquery as cq
    from OCC.Core.BRepAdaptor import BRepAdaptor_Surface, BRepAdaptor_Curve
    from OCC.Core.GeomAbs import (
        GeomAbs_Cylinder, GeomAbs_Plane, GeomAbs_Circle, GeomAbs_Torus,
    )
    from OCC.Core.TopAbs import TopAbs_REVERSED
    from OCC.Core.BRepBndLib import brepbndlib
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.GProp import GProp_GProps
    from OCC.Core.BRepGProp import brepgprop
    CADQUERY_AVAILABLE = True
except ImportError:
    CADQUERY_AVAILABLE = False
    logger.warning(
        "cadquery not installed — STEP feature recognition unavailable. "
        "Install: pip install cadquery"
    )


# Deterministic feature-type → class-index mapping.
# Add new types here; existing indices must not change (would break trained models).
FEATURE_CLASS_ORDER = [
    "hole",           # 0 — blind or through cylindrical cavity
    "threaded_hole",  # 1 — hole with thread geometry
    "boss",           # 2 — raised cylindrical protrusion
    "slot",           # 3 — open rectangular groove
    "pocket",         # 4 — closed rectangular recess
    "chamfer",        # 5 — bevelled edge face
    "fillet",         # 6 — rounded edge between two faces
    "planar_face",    # 7 — large flat surface (background / reference)
]

# Cylinders with radius below this (mm) are classified as fillets, not holes.
_FILLET_RADIUS_MM = 3.0

# Minimum radius to consider at all (filters mesh artifacts).
_MIN_RADIUS_MM = 0.05

# Planar face must be this many times larger than the average planar face
# area to be labelled "planar_face" (main body surface).
_PLANAR_FACE_AREA_FACTOR = 2.0

# A face whose normal has no single component > this value is at ≈45° = chamfer.
_CHAMFER_NORMAL_MAX_COMPONENT = 0.88   # cos(28°) — generous


@dataclass
class RecognizedFeature:
    """A single manufacturing feature extracted from a B-Rep model."""

    feature_type: str
    center_x: float
    center_y: float
    center_z: float
    normal_x: float = 0.0
    normal_y: float = 0.0
    normal_z: float = 1.0
    radius:  Optional[float] = None
    depth:   Optional[float] = None
    width:   Optional[float] = None
    length:  Optional[float] = None
    properties: dict = field(default_factory=dict)

    @property
    def class_index(self) -> int:
        try:
            return FEATURE_CLASS_ORDER.index(self.feature_type)
        except ValueError:
            return len(FEATURE_CLASS_ORDER)

    def to_dict(self) -> dict:
        return {
            "feature_type": self.feature_type,
            "class_index": self.class_index,
            "center": [self.center_x, self.center_y, self.center_z],
            "normal": [self.normal_x, self.normal_y, self.normal_z],
            "radius": self.radius,
            "depth": self.depth,
            "width": self.width,
            "length": self.length,
            "properties": self.properties,
        }


@dataclass
class ParseResult:
    """Outcome of parsing a STEP file."""

    success: bool
    features: list   # list[RecognizedFeature]
    stl_path: Optional[str] = None
    class_names: list = field(default_factory=list)  # ordered unique feature types present
    error: Optional[str] = None
    stats: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

class STEPParser:
    """
    Parses a STEP/STP file, recognises manufacturing features, and exports STL.

    Usage::

        parser = STEPParser()
        result = parser.parse("bracket.step", output_dir="storage/uploads/xxx")
        if result.success:
            for f in result.features:
                print(f.feature_type, f.center_x, f.center_y, f.center_z)
    """

    def parse(self, step_path: str, output_dir: str) -> ParseResult:
        """
        Args:
            step_path:  Absolute path to the .step / .stp file.
            output_dir: Directory where the exported STL will be written.

        Returns:
            ParseResult — always succeeds structurally; check ``.success``.
        """
        if not CADQUERY_AVAILABLE:
            return ParseResult(
                success=False,
                features=[],
                error=(
                    "cadquery is not installed. "
                    "Run: pip install cadquery"
                ),
            )

        step_path = Path(step_path)
        if not step_path.exists():
            return ParseResult(
                success=False,
                features=[],
                error=f"STEP file not found: {step_path}",
            )

        try:
            logger.info(f"Loading STEP: {step_path}")
            shape = cq.importers.importStep(str(step_path))

            logger.info("Running feature recognition …")
            recognizer = _FeatureRecognizer()
            features = recognizer.recognize(shape)

            # Export STL for Blender
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            stl_path = output_dir / f"{step_path.stem}.stl"
            cq.exporters.export(shape, str(stl_path))
            logger.info(f"STL exported: {stl_path}")

            # Build ordered class name list (only types actually present)
            seen: set = set()
            class_names = []
            for ft in FEATURE_CLASS_ORDER:
                if ft not in seen and any(f.feature_type == ft for f in features):
                    class_names.append(ft)
                    seen.add(ft)

            by_type = {}
            for f in features:
                by_type[f.feature_type] = by_type.get(f.feature_type, 0) + 1

            logger.info(
                f"Recognised {len(features)} features across "
                f"{len(class_names)} types: {by_type}"
            )

            return ParseResult(
                success=True,
                features=features,
                stl_path=str(stl_path),
                class_names=class_names,
                stats={"total": len(features), "by_type": by_type},
            )

        except Exception as exc:
            logger.exception(f"STEP parse failed for {step_path}: {exc}")
            return ParseResult(success=False, features=[], error=str(exc))


# ---------------------------------------------------------------------------
# Internal recogniser
# ---------------------------------------------------------------------------

class _FeatureRecognizer:
    """Analyses B-Rep topology to classify manufacturing features."""

    def recognize(self, shape) -> list:
        """Return a flat list of RecognizedFeature for all detected features."""
        # cadquery 2.x: importStep returns a Shape (Solid or Compound).
        # .Faces() / .Edges() work directly on it.
        features: list = []
        features.extend(self._cylindrical_features(shape))
        features.extend(self._planar_features(shape))
        return features

    # ------------------------------------------------------------------
    # Cylindrical faces → holes, bosses, fillets
    # ------------------------------------------------------------------

    def _cylindrical_features(self, shape) -> list:
        features = []
        seen_keys: set = set()

        for face in shape.Faces():
            adaptor = BRepAdaptor_Surface(face.wrapped)
            if adaptor.GetType() != GeomAbs_Cylinder:
                continue

            cylinder  = adaptor.Cylinder()
            radius    = cylinder.Radius()

            if radius < _MIN_RADIUS_MM:
                continue

            axis_loc = cylinder.Location()    # gp_Pnt
            axis_dir = cylinder.Axis().Direction()  # gp_Dir

            # Use the cadquery face centroid as the feature centre
            cq_center = face.Center()  # cq.Vector
            cx, cy, cz = cq_center.x, cq_center.y, cq_center.z

            # De-duplicate: same axis location + radius = same cylinder
            key = (round(cx, 1), round(cy, 1), round(cz, 1), round(radius, 2))
            if key in seen_keys:
                continue
            seen_keys.add(key)

            depth = self._cylinder_depth(face)

            if radius < _FILLET_RADIUS_MM:
                ftype = "fillet"
            else:
                # TopAbs_REVERSED → inner surface → hole
                is_inner = (face.wrapped.Orientation() == TopAbs_REVERSED)
                ftype = "hole" if is_inner else "boss"

            features.append(RecognizedFeature(
                feature_type=ftype,
                center_x=round(cx, 4),
                center_y=round(cy, 4),
                center_z=round(cz, 4),
                normal_x=round(axis_dir.X(), 4),
                normal_y=round(axis_dir.Y(), 4),
                normal_z=round(axis_dir.Z(), 4),
                radius=round(radius, 4),
                depth=round(depth, 4) if depth is not None else None,
                properties={"surface_area": round(self._face_area(face), 4)},
            ))

        return features

    # ------------------------------------------------------------------
    # Planar faces → chamfers, large flat surfaces
    # ------------------------------------------------------------------

    def _planar_features(self, shape) -> list:
        features = []

        planar = [
            f for f in shape.Faces()
            if BRepAdaptor_Surface(f.wrapped).GetType() == GeomAbs_Plane
        ]
        if not planar:
            return features

        areas = [self._face_area(f) for f in planar]
        avg_area = sum(areas) / len(areas) if areas else 1.0

        for face, area in zip(planar, areas):
            center = face.Center()
            normal = face.normalAt(center)   # cq.Vector

            nx_a = abs(normal.x)
            ny_a = abs(normal.y)
            nz_a = abs(normal.z)
            max_component = max(nx_a, ny_a, nz_a)

            # Chamfer heuristic:
            #   - face is small (< half average)
            #   - normal has no single dominant axis  → diagonal orientation
            is_small    = area < avg_area * 0.5
            is_diagonal = max_component < _CHAMFER_NORMAL_MAX_COMPONENT

            if is_small and is_diagonal:
                ftype = "chamfer"
            elif area > avg_area * _PLANAR_FACE_AREA_FACTOR:
                ftype = "planar_face"
            else:
                continue   # mid-size planar face — not interesting for detection

            features.append(RecognizedFeature(
                feature_type=ftype,
                center_x=round(center.x, 4),
                center_y=round(center.y, 4),
                center_z=round(center.z, 4),
                normal_x=round(normal.x, 4),
                normal_y=round(normal.y, 4),
                normal_z=round(normal.z, 4),
                properties={"area": round(area, 4)},
            ))

        return features

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _cylinder_depth(self, face) -> Optional[float]:
        """Estimate depth as the bounding-box extent along the cylinder axis."""
        try:
            adaptor  = BRepAdaptor_Surface(face.wrapped)
            axis_dir = adaptor.Cylinder().Axis().Direction()

            bbox = Bnd_Box()
            brepbndlib.Add(face.wrapped, bbox)
            xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()

            depth = (
                abs(axis_dir.X()) * (xmax - xmin) +
                abs(axis_dir.Y()) * (ymax - ymin) +
                abs(axis_dir.Z()) * (zmax - zmin)
            )
            return depth if depth > 0 else None
        except Exception:
            return None

    def _face_area(self, face) -> float:
        try:
            props = GProp_GProps()
            brepgprop.SurfaceProperties(face.wrapped, props)
            return props.Mass()
        except Exception:
            try:
                return face.Area()
            except Exception:
                return 0.0
