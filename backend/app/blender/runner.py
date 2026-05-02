"""
Blender subprocess execution and management.
"""
import os
import subprocess
import re
import logging
from pathlib import Path
from typing import Optional, Callable
from uuid import UUID

from app.blender.config import (
    DEFAULT_BLENDER_PATH,
    BlenderRenderConfig,
    BlenderExecutionResult,
)

logger = logging.getLogger(__name__)


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
    ) -> BlenderExecutionResult:
        """
        Render synthetic data from a .blend / .obj / .stl / .fbx scene file.
        Uses the hardcoded desk-scene Blender script (legacy pipeline).
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        script_path = self._prepare_legacy_script(output_dir, config)

        cmd = [
            self.blender_path,
            blend_file_path,
            "--background",
            "--python", script_path,
        ]

        return self._execute_blender(cmd, output_dir, config.num_renders)

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

        project_root = Path(__file__).parent.parent.parent.parent
        script_path  = project_root / "blender" / "step_render_script.py"

        if not script_path.exists():
            return BlenderExecutionResult(
                success=False,
                output_dir=output_dir,
                images_generated=0,
                labels_generated=0,
                error_message=f"step_render_script.py not found at {script_path}",
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

    def _prepare_legacy_script(
        self,
        output_dir: str,
        config: BlenderRenderConfig,
    ) -> str:
        """
        Locate and configure the legacy desk-scene wrapper script.
        Sets environment variables that eevee_api_wrapper.py reads.
        """
        project_root = Path(__file__).parent.parent.parent.parent
        script_path  = project_root / "blender" / "eevee_api_wrapper.py"

        if not script_path.exists():
            logger.warning(
                f"Wrapper not found at {script_path}, falling back to direct script"
            )
            script_path = project_root / "blender" / "eevee_desk_scene17_dualpass.py"

        os.environ["BLENDER_OUTPUT_DIR"]    = output_dir
        os.environ["BLENDER_NUM_RENDERS"]   = str(config.num_renders)
        os.environ["BLENDER_RESOLUTION_X"]  = str(config.resolution_x)
        os.environ["BLENDER_RESOLUTION_Y"]  = str(config.resolution_y)
        os.environ["BLENDER_EEVEE_SAMPLES"] = str(config.eevee_samples)

        logger.info(
            f"Legacy script: {script_path}  "
            f"{config.num_renders} renders @ {config.resolution_x}x{config.resolution_y}"
        )
        return str(script_path)
