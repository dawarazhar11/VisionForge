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
    BlenderExecutionResult
)

logger = logging.getLogger(__name__)


class BlenderRunner:
    """Manages Blender subprocess execution for synthetic data generation."""

    def __init__(
        self,
        blender_path: str = DEFAULT_BLENDER_PATH,
        progress_callback: Optional[Callable[[int], None]] = None
    ):
        """
        Initialize Blender runner.

        Args:
            blender_path: Path to Blender executable
            progress_callback: Optional callback function for progress updates (0-100)
        """
        self.blender_path = blender_path
        self.progress_callback = progress_callback

        # Check if Blender exists
        if not os.path.exists(blender_path):
            logger.warning(f"Blender not found at {blender_path}")

    def render_synthetic_data(
        self,
        blend_file_path: str,
        output_dir: str,
        config: BlenderRenderConfig,
        project_id: UUID,
        job_id: UUID
    ) -> BlenderExecutionResult:
        """
        Execute Blender rendering with progress tracking.

        Args:
            blend_file_path: Path to .blend file
            output_dir: Directory for output images and labels
            config: Rendering configuration
            project_id: Project UUID
            job_id: Job UUID for tracking

        Returns:
            BlenderExecutionResult with success status and metadata
        """
        try:
            # Ensure output directory exists
            Path(output_dir).mkdir(parents=True, exist_ok=True)

            # Create Python script path for Blender execution
            script_path = self._prepare_blender_script(
                output_dir=output_dir,
                config=config
            )

            # Build Blender command
            cmd = [
                self.blender_path,
                blend_file_path,
                "--background",
                "--python", script_path
            ]

            logger.info(f"Starting Blender render: {' '.join(cmd)}")

            # Execute Blender subprocess with real-time output
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace'  # Replace undecodable characters with �
            )

            output_lines = []
            images_generated = 0

            # Parse output in real-time
            for line in process.stdout:
                output_lines.append(line)
                logger.debug(f"Blender: {line.strip()}")

                # Parse progress from Blender output
                progress_match = re.search(r"Rendering image (\d+)/(\d+)", line)
                if progress_match:
                    current = int(progress_match.group(1))
                    total = int(progress_match.group(2))
                    images_generated = current

                    if self.progress_callback:
                        progress_percent = int((current / total) * 100)
                        self.progress_callback(progress_percent)

                # Parse completion message
                if "Rendering complete!" in line:
                    logger.info("Blender rendering completed successfully")

            # Wait for process to complete
            return_code = process.wait()

            if return_code != 0:
                error_msg = f"Blender exited with code {return_code}"
                blender_log = "\n".join(output_lines[-100:])  # Last 100 lines
                logger.error(f"{error_msg}\nBlender output:\n{blender_log}")
                return BlenderExecutionResult(
                    success=False,
                    output_dir=output_dir,
                    images_generated=images_generated,
                    labels_generated=0,
                    error_message=f"{error_msg}\n\nBlender output:\n{blender_log}",
                    blender_log=blender_log
                )

            # Count generated files
            images_count = len(list(Path(output_dir).glob("*.png")))
            labels_count = len(list(Path(output_dir).glob("*.txt")))

            logger.info(
                f"Rendering complete: {images_count} images, {labels_count} labels"
            )

            return BlenderExecutionResult(
                success=True,
                output_dir=output_dir,
                images_generated=images_count,
                labels_generated=labels_count,
                error_message=None,
                blender_log="\n".join(output_lines[-100:])  # Last 100 lines
            )

        except FileNotFoundError as e:
            error_msg = f"Blender executable not found: {self.blender_path}"
            logger.error(error_msg)
            return BlenderExecutionResult(
                success=False,
                output_dir=output_dir,
                images_generated=0,
                labels_generated=0,
                error_message=error_msg,
                blender_log=str(e)
            )
        except Exception as e:
            error_msg = f"Blender execution failed: {str(e)}"
            logger.error(error_msg)
            return BlenderExecutionResult(
                success=False,
                output_dir=output_dir,
                images_generated=0,
                labels_generated=0,
                error_message=error_msg,
                blender_log=str(e)
            )

    def _prepare_blender_script(
        self,
        output_dir: str,
        config: BlenderRenderConfig
    ) -> str:
        """
        Prepare Blender Python script with configuration.

        Args:
            output_dir: Output directory path
            config: Rendering configuration

        Returns:
            Path to prepared Python script
        """
        # Use the API wrapper script that configures the existing rendering script
        # Path goes from backend/app/blender/runner.py -> project root
        project_root = Path(__file__).parent.parent.parent.parent
        script_path = project_root / "eevee_api_wrapper.py"

        if not script_path.exists():
            # Fallback to direct script (will use hardcoded config)
            logger.warning(f"Wrapper script not found at {script_path}, using direct script")
            script_path = project_root / "eevee_desk_scene17_dualpass.py"

        # Set environment variables for wrapper script
        os.environ["BLENDER_OUTPUT_DIR"] = output_dir
        os.environ["BLENDER_NUM_RENDERS"] = str(config.num_renders)
        os.environ["BLENDER_RESOLUTION_X"] = str(config.resolution_x)
        os.environ["BLENDER_RESOLUTION_Y"] = str(config.resolution_y)
        os.environ["BLENDER_EEVEE_SAMPLES"] = str(config.eevee_samples)
        
        logger.info(f"Using Blender script: {script_path}")
        logger.info(f"Render config: {config.num_renders} images @ {config.resolution_x}x{config.resolution_y}")

        return str(script_path)

    def check_gpu_availability(self) -> dict:
        """
        Check if GPU acceleration is available.

        Returns:
            Dictionary with GPU information
        """
        try:
            # Run Blender to check compute devices
            cmd = [
                self.blender_path,
                "--background",
                "--python-expr",
                "import bpy; print(bpy.context.preferences.addons['cycles'].preferences.devices)"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            output = result.stdout

            # Parse GPU information from output
            has_cuda = "CUDA" in output
            has_optix = "OPTIX" in output
            has_metal = "METAL" in output

            return {
                "available": has_cuda or has_optix or has_metal,
                "cuda": has_cuda,
                "optix": has_optix,
                "metal": has_metal,
                "raw_output": output
            }

        except Exception as e:
            logger.error(f"Failed to check GPU availability: {e}")
            return {
                "available": False,
                "error": str(e)
            }
