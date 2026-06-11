"""
STEP assembly reader — extracts named components for part-level labels (DAW-118).

Uses OCP's XDE (STEPCAFControl) reader, which preserves the assembly tree
and component names that plain `cadquery.importers.importStep` drops.
Fusion 360, SolidWorks, and Inventor all carry component names into STEP
PRODUCT entities, so those names become YOLO classes.

All OCP imports are lazy: cadquery-ocp has no ARM64 Linux wheels, and the
worker must still import this module to report a clean error.
"""
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from loguru import logger

# CAD-tool default names that carry no labelling value
_DEFAULT_NAME_RE = re.compile(
    r"^(component|body|part|solid|shape|compound|mirror|boolean|"
    r"unknown|none|open cascade.*|cut|extrude|loft|revolve)[ _\-]?\d*(\(\d+\))?$",
    re.IGNORECASE,
)


@dataclass
class AssemblyComponent:
    """One named solid extracted from a STEP assembly."""
    name: str
    stl_path: str


@dataclass
class AssemblyParseResult:
    success: bool
    components: List[AssemblyComponent] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def component_names(self) -> List[str]:
        return [c.name for c in self.components]


def is_default_part_name(name: str) -> bool:
    """True for CAD-tool placeholder names like 'Body1' or 'Component_3'."""
    return not name.strip() or bool(_DEFAULT_NAME_RE.match(name.strip()))


def sanitize_part_name(name: str, index: int) -> str:
    """Normalize a component name into a usable class name."""
    cleaned = re.sub(r"\s+", "_", name.strip()) if name else ""
    cleaned = re.sub(r"[^\w\-.]", "", cleaned)
    return cleaned or f"part_{index + 1}"


def read_step_assembly(step_path: str, output_dir: str) -> AssemblyParseResult:
    """
    Read a STEP file's assembly tree and export one STL per component.

    Returns success with an empty/one-element component list for
    single-part files — the caller decides whether to use part mode
    (>= 2 components) or fall back to feature recognition.
    """
    try:
        from OCP.IFSelect import IFSelect_RetDone
        from OCP.STEPCAFControl import STEPCAFControl_Reader
        from OCP.TCollection import TCollection_ExtendedString
        from OCP.TDataStd import TDataStd_Name
        from OCP.TDF import TDF_Label, TDF_LabelSequence
        from OCP.TDocStd import TDocStd_Document
        from OCP.XCAFDoc import XCAFDoc_DocumentTool
        from cadquery.occ_impl.shapes import Shape
    except ImportError as exc:
        return AssemblyParseResult(
            success=False,
            error=f"cadquery/OCP is not installed: {exc}",
        )

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    try:
        doc = TDocStd_Document(TCollection_ExtendedString("MDTV-XCAF"))
        reader = STEPCAFControl_Reader()
        reader.SetNameMode(True)

        if reader.ReadFile(str(step_path)) != IFSelect_RetDone:
            return AssemblyParseResult(success=False, error="STEP read failed")
        if not reader.Transfer(doc):
            return AssemblyParseResult(success=False, error="STEP transfer failed")

        shape_tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())

        def label_name(label: TDF_Label) -> str:
            attr = TDataStd_Name()
            if label.FindAttribute(TDataStd_Name.GetID_s(), attr):
                return TCollection_ExtendedString.ToExtString(attr.Get()) \
                    if hasattr(TCollection_ExtendedString, "ToExtString") \
                    else attr.Get().ToExtString()
            return ""

        shapes: List[tuple] = []  # (name, TopoDS_Shape with location applied)

        def walk(label: TDF_Label):
            if shape_tool.IsAssembly_s(label):
                children = TDF_LabelSequence()
                shape_tool.GetComponents_s(label, children)
                for i in range(1, children.Length() + 1):
                    walk(children.Value(i))
            elif shape_tool.IsReference_s(label):
                referred = TDF_Label()
                shape_tool.GetReferredShape_s(label, referred)
                if shape_tool.IsAssembly_s(referred):
                    # Instance of a sub-assembly: recurse into the definition
                    walk(referred)
                else:
                    # Instance name first (e.g. "bolt_m4:2"), else prototype name
                    name = label_name(label) or label_name(referred)
                    shapes.append((name, shape_tool.GetShape_s(label)))
            else:
                shapes.append((label_name(label), shape_tool.GetShape_s(label)))

        free = TDF_LabelSequence()
        shape_tool.GetFreeShapes(free)
        for i in range(1, free.Length() + 1):
            walk(free.Value(i))

        components: List[AssemblyComponent] = []
        for idx, (raw_name, topo_shape) in enumerate(shapes):
            name = sanitize_part_name(raw_name, idx)
            # Instance names like "bracket:1" → "bracket"
            name = re.sub(r"[:_]\d+$", "", name) or f"part_{idx + 1}"
            stl_path = out / f"component_{idx:03d}.stl"
            Shape.cast(topo_shape).exportStl(str(stl_path), tolerance=0.1)
            components.append(AssemblyComponent(name=name, stl_path=str(stl_path)))

        logger.info(
            f"STEP assembly: {len(components)} component(s): "
            f"{[c.name for c in components]}"
        )
        return AssemblyParseResult(success=True, components=components)

    except Exception as exc:
        logger.warning(f"STEP assembly read failed: {exc}")
        return AssemblyParseResult(success=False, error=str(exc))
