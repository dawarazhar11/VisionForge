"""
Blender subprocess execution and management.
"""
import json
import os
import subprocess
import re
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Callable
from uuid import UUID

from app.blender.class_map import build_class_map_payload
from app.blender.config import (
    DEFAULT_BLENDER_PATH,
    BlenderRenderConfig,
    BlenderExecutionResult,
)

logger = logging.getLogger(__name__)


def find_blender_script(script_name: str) -> Optional[Path]:
    """
    Locate a render script from the repo's blender/ directory.

    Checked in order:
      1. $BLENDER_SCRIPTS_DIR (set in Docker, where blender/ is volume-mounted)
      2. <repo root>/blender (local dev: this file lives in backend/app/blender/)
    """
    candidates = []
    env_dir = os.environ.get("BLENDER_SCRIPTS_DIR")
    if env_dir:
        candidates.append(Path(env_dir))
    candidates.append(Path(__file__).parent.parent.parent.parent / "blender")

    for directory in candidates:
        path = directory / script_name
        if path.exists():
            return path

    logger.error(f"{script_name} not found in: {[str(c) for c in candidates]}")
    return None


class BlenderRunner:
    """Manages Blender subprocess execution for synthetic data generation."""

    def __init__(
        self,
        blender_path: str = DEFAULT_BLENDER_PATH,
        progress_callback: Optional[Callable[[int], None]] = None,
    ):
        self.blender_path = blender_path
        self.progress_callback = progress_callback

        if not os.path.exists(blender_path):
            logger.warning(f"Blender not found at {blender_path}")

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def render_synthetic_data(
        self,
        blend_file_path: str,
        output_dir: str,
        config: BlenderRenderConfig,
        project_id: UUID,
        job_id: UUID,
        project_metadata: Optional[Dict[str, Any]] = None,
    ) -> BlenderExecutionResult:
        """
        Render synthetic data from a .blend file using the generic class-map pipeline.
        """
        return self.render_blend_geometry(
            blend_file_path=blend_file_path,
            output_dir=output_dir,
            config=config,
            project_metadata=project_metadata,
        )

    def render_blend_geometry(
        self,
        blend_file_path: str,
        output_dir: str,
        config: BlenderRenderConfig,
        project_metadata: Optional[Dict[str, Any]] = None,
    ) -> BlenderExecutionResult:
        """
        Render synthetic data from a .blend file with configurable class maps.
        Falls back to desk-scene preset or per-object auto classes inside Blender.
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        class_map_path = self._write_blend_class_map_hint(
            output_dir, project_metadata
        )
        script_path, env = self._prepare_generic_blend_script(
            output_dir, config, class_map_path
        )

        cmd = [
            self.blender_path,
            blend_file_path,
            "--background",
            "--python", script_path,
        ]

        result = self._execute_blender(
            cmd, output_dir, config.num_renders, env=env
        )
        return self._attach_class_map_from_output(result)

    def render_step_geometry(
        self,
        stl_path: str,
        features_json_path: str,
        output_dir: str,
        config: BlenderRenderConfig,
    ) -> BlenderExecutionResult:
        """
        Render synthetic data from a STEP-converted STL + feature map.
        Uses the generic step_render_script.py — no blend file required.
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Pass config to the Blender script via environment variables
        env = os.environ.copy()
        env.update({
            "VFORGE_STL_PATH":       stl_path,
            "VFORGE_FEATURES_JSON":  features_json_path,
            "VFORGE_OUTPUT_DIR":     output_dir,
            "VFORGE_NUM_RENDERS":    str(config.num_renders),
            "VFORGE_RESOLUTION_X":   str(config.resolution_x),
            "VFORGE_RESOLUTION_Y":   str(config.resolution_y),
            "VFORGE_EEVEE_SAMPLES":  str(config.eevee_samples),
        })

        script_path = find_blender_script("step_render_script.py")

        if script_path is None or not script_path.exists():
            return BlenderExecutionResult(
                success=False,
                output_dir=output_dir,
                images_generated=0,
                labels_generated=0,
                error_message=(
                    "step_render_script.py not found in any Blender scripts "
                    "location (set BLENDER_SCRIPTS_DIR)"
                ),
            )

        # No blend file — Blender opens in an empty state and the script
        # handles everything via bpy.ops.wm.stl_import.
        cmd = [
            self.blender_path,
            "--background",
            "--python", str(script_path),
        ]

        logger.info(f"render_step_geometry: STL={stl_path}  out={output_dir}")
        return self._execute_blender(cmd, output_dir, config.num_renders, env=env)

    def render_step_parts(
        self,
        parts_json_path: str,
        output_dir: str,
        config: BlenderRenderConfig,
    ) -> BlenderExecutionResult:
        """
        Render a multi-component STEP assembly: one STL per named part,
        each part its own YOLO class (DAW-118).
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        script_path = find_blender_script("step_parts_render_script.py")
        if script_path is None:
            return BlenderExecutionResult(
                success=False,
                output_dir=output_dir,
                images_generated=0,
                labels_generated=0,
                error_message=(
                    "step_parts_render_script.py not found in any Blender "
                    "scripts location (set BLENDER_SCRIPTS_DIR)"
                ),
            )

        env = os.environ.copy()
        env.update({
            "VFORGE_PARTS_JSON":    parts_json_path,
            "VFORGE_OUTPUT_DIR":    output_dir,
            "VFORGE_NUM_RENDERS":   str(config.num_renders),
            "VFORGE_RESOLUTION_X":  str(config.resolution_x),
            "VFORGE_RESOLUTION_Y":  str(config.resolution_y),
            "VFORGE_EEVEE_SAMPLES": str(config.eevee_samples),
        })

        # Per-part isolation passes (base part fixed, others hidden, each
        # target rendered one at a time) — on by default for robust per-part
        # examples. Configurable via the render job config.
        env["VFORGE_ISOLATION"] = "0" if getattr(config, "isolation", True) is False else "1"
        base_part = getattr(config, "base_part", None)
        if base_part:
            env["VFORGE_BASE_PART"] = str(base_part)
        full_frac = getattr(config, "isolation_full_frac", None)
        if full_frac is not None:
            env["VFORGE_ISOLATION_FULL_FRAC"] = str(full_frac)

        cmd = [
            self.blender_path,
            "--background",
            "--python", str(script_path),
        ]

        logger.info(
            f"render_step_parts: manifest={parts_json_path}  out={output_dir}  "
            f"isolation={env['VFORGE_ISOLATION']}"
        )
        result = self._execute_blender(cmd, output_dir, config.num_renders, env=env)
        return self._attach_class_map_from_output(result)

    def check_gpu_availability(self) -> dict:
        try:
            cmd = [
                self.blender_path,
                "--background",
                "--python-expr",
                "import bpy; print(bpy.context.preferences.addons['cycles'].preferences.devices)",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            output = result.stdout
            return {
                "available": any(x in output for x in ("CUDA", "OPTIX", "METAL")),
                "cuda":   "CUDA"   in output,
                "optix":  "OPTIX"  in output,
                "metal":  "METAL"  in output,
                "raw_output": output,
            }
        except Exception as e:
            return {"available": False, "error": str(e)}

    # ──────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _execute_blender(
        self,
        cmd: list,
        output_dir: str,
        num_renders: int,
        env: Optional[dict] = None,
    ) -> BlenderExecutionResult:
        """
        Run a Blender subprocess, stream its output, and parse progress.
        Shared by both render_synthetic_data and render_step_geometry.
        """
        logger.info(f"Blender cmd: {' '.join(cmd)}")

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )

            output_lines   = []
            images_written = 0

            for line in process.stdout:
                output_lines.append(line)
                logger.debug(f"Blender: {line.rstrip()}")

                # "Rendering image N/M" — legacy script format
                m = re.search(r"Rendering image (\d+)/(\d+)", line)
                if m:
                    current = int(m.group(1))
                    total   = int(m.group(2))
                    images_written = current
                    if self.progress_callback:
                        self.progress_callback(int(current / total * 100))

                # "Rendering image N/M" — generic STEP script format
                m2 = re.search(r"Rendering image (\d+)/(\d+)", line)
                if not m2:
                    # Generic script prints "Rendering image N/M  annotations=..."
                    m2 = re.search(r"render\s+(\d+)/(\d+)", line, re.IGNORECASE)
                if m2 and not m:
                    current = int(m2.group(1))
                    total   = int(m2.group(2))
                    images_written = current
                    if self.progress_callback:
                        self.progress_callback(int(current / total * 100))

                if "Rendering complete" in line or "VisionForge" in line and "Done" in line:
                    logger.info("Blender rendering completed")

            return_code = process.wait()

            if return_code != 0:
                log_tail = "".join(output_lines[-100:])
                error_msg = f"Blender exited with code {return_code}"
                logger.error(f"{error_msg}\n{log_tail}")
                return BlenderExecutionResult(
                    success=False,
                    output_dir=output_dir,
                    images_generated=images_written,
                    labels_generated=0,
                    error_message=f"{error_msg}\n\n{log_tail}",
                    blender_log=log_tail,
                )

            out_path = Path(output_dir)
            images_count = len(list(out_path.glob("*.png")))
            labels_count = len(list(out_path.glob("*.txt")))

            logger.info(f"Render done: {images_count} images, {labels_count} labels")

            return BlenderExecutionResult(
                success=True,
                output_dir=output_dir,
                images_generated=images_count,
                labels_generated=labels_count,
                error_message=None,
                blender_log="".join(output_lines[-100:]),
            )

        except FileNotFoundError:
            error_msg = f"Blender executable not found: {self.blender_path}"
            logger.error(error_msg)
            return BlenderExecutionResult(
                success=False,
                output_dir=output_dir,
                images_generated=0,
                labels_generated=0,
                error_message=error_msg,
            )
        except Exception as e:
            error_msg = f"Blender execution failed: {e}"
            logger.error(error_msg)
            return BlenderExecutionResult(
                success=False,
                output_dir=output_dir,
                images_generated=0,
                labels_generated=0,
                error_message=error_msg,
                blender_log=str(e),
            )

    def _write_blend_class_map_hint(
        self,
        output_dir: str,
        project_metadata: Optional[Dict[str, Any]],
    ) -> Optional[str]:
        """
        When metadata carries an explicit class_map, write it for the Blender script.
        Object discovery still happens in Blender; desk/auto presets are resolved there.
        """
        from app.blender.class_map import parse_metadata_class_map

        parsed = parse_metadata_class_map(project_metadata)
        if parsed is None:
            return None

        obj_map, class_names = parsed
        payload = build_class_map_payload(obj_map, class_names, "metadata")
        path = Path(output_dir) / "class_map_input.json"
        path.write_text(json.dumps(payload, indent=2))
        return str(path)

    def _prepare_generic_blend_script(
        self,
        output_dir: str,
        config: BlenderRenderConfig,
        class_map_path: Optional[str],
    ) -> tuple:
        """Configure env vars for generic_blend_render_script.py."""
        script_path = find_blender_script("generic_blend_render_script.py")

        if script_path is None:
            raise FileNotFoundError(
                "generic_blend_render_script.py not found in any Blender "
                "scripts location (set BLENDER_SCRIPTS_DIR)"
            )

        env = os.environ.copy()
        env.update({
            "VFORGE_OUTPUT_DIR":    output_dir,
            "VFORGE_NUM_RENDERS":   str(config.num_renders),
            "VFORGE_RESOLUTION_X":  str(config.resolution_x),
            "VFORGE_RESOLUTION_Y":  str(config.resolution_y),
            "VFORGE_EEVEE_SAMPLES": str(config.eevee_samples),
        })
        if class_map_path:
            env["VFORGE_CLASS_MAP_JSON"] = class_map_path

        logger.info(
            f"Generic blend script: {script_path}  "
            f"{config.num_renders} renders @ {config.resolution_x}x{config.resolution_y}"
        )
        return str(script_path), env

    def _attach_class_map_from_output(
        self, result: BlenderExecutionResult
    ) -> BlenderExecutionResult:
        """Read class_map.json written by the Blender script into the result."""
        if not result.success:
            return result

        map_path = Path(result.output_dir) / "class_map.json"
        if not map_path.exists():
            return result

        try:
            data = json.loads(map_path.read_text())
            return result.model_copy(update={
                "class_names": data.get("class_names"),
                "class_map_source": data.get("source"),
            })
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(f"Could not read class_map.json: {exc}")
            return result
