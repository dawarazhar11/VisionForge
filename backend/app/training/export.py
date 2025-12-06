"""
Model export utilities for multi-platform deployment.

Exports trained YOLO models to various formats:
- TFLite for Android/Flutter
- Core ML for iOS
- ONNX for Windows/Linux
"""
from pathlib import Path
from typing import Dict, Optional
from loguru import logger
import os


def export_model_tflite(
    model_path: str,
    output_dir: str,
    imgsz: int = 640,
    int8: bool = False
) -> str:
    """
    Export YOLO model to TensorFlow Lite format for Android/Flutter.

    Args:
        model_path: Path to trained YOLO model (.pt file)
        output_dir: Directory to save exported model
        imgsz: Input image size (default: 640x640)
        int8: Use INT8 quantization (default: False, uses FP16)

    Returns:
        Path to exported .tflite file

    Raises:
        FileNotFoundError: If model file doesn't exist
        RuntimeError: If export fails
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        raise ImportError(
            "Ultralytics package not installed. "
            "Install with: pip install ultralytics"
        )

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Loading YOLO model from {model_path}")
    model = YOLO(model_path)

    logger.info(f"Exporting to TFLite (imgsz={imgsz}, int8={int8})...")
    tflite_path = model.export(
        format='tflite',
        int8=int8,  # INT8 quantization if True, FP16 if False
        imgsz=imgsz,
        nms=True  # Include NMS in model
    )

    logger.info(f"TFLite model exported successfully: {tflite_path}")
    return str(tflite_path)


def export_model_coreml(
    model_path: str,
    output_dir: str,
    imgsz: int = 640,
    half: bool = True
) -> str:
    """
    Export YOLO model to Core ML format for iOS.

    Args:
        model_path: Path to trained YOLO model (.pt file)
        output_dir: Directory to save exported model
        imgsz: Input image size (default: 640x640)
        half: Use FP16 precision (default: True)

    Returns:
        Path to exported .mlpackage directory

    Raises:
        FileNotFoundError: If model file doesn't exist
        RuntimeError: If export fails
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        raise ImportError(
            "Ultralytics package not installed. "
            "Install with: pip install ultralytics"
        )

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Loading YOLO model from {model_path}")
    model = YOLO(model_path)

    logger.info(f"Exporting to Core ML (imgsz={imgsz}, half={half})...")
    coreml_path = model.export(
        format='coreml',
        nms=True,
        imgsz=imgsz,
        half=half  # FP16 for smaller size
    )

    logger.info(f"Core ML model exported successfully: {coreml_path}")
    return str(coreml_path)


def export_model_onnx(
    model_path: str,
    output_dir: str,
    imgsz: int = 640,
    opset: int = 12,
    dynamic: bool = False
) -> str:
    """
    Export YOLO model to ONNX format for Windows/Linux.

    Args:
        model_path: Path to trained YOLO model (.pt file)
        output_dir: Directory to save exported model
        imgsz: Input image size (default: 640x640)
        opset: ONNX opset version (default: 12)
        dynamic: Use dynamic input shapes (default: False)

    Returns:
        Path to exported .onnx file

    Raises:
        FileNotFoundError: If model file doesn't exist
        RuntimeError: If export fails
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        raise ImportError(
            "Ultralytics package not installed. "
            "Install with: pip install ultralytics"
        )

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Loading YOLO model from {model_path}")
    model = YOLO(model_path)

    logger.info(f"Exporting to ONNX (imgsz={imgsz}, opset={opset}, dynamic={dynamic})...")
    onnx_path = model.export(
        format='onnx',
        imgsz=imgsz,
        opset=opset,
        dynamic=dynamic  # Fixed input size for faster inference
    )

    logger.info(f"ONNX model exported successfully: {onnx_path}")
    return str(onnx_path)


def export_all_formats(
    model_path: str,
    output_dir: str,
    imgsz: int = 640
) -> Dict[str, str]:
    """
    Export trained YOLO model to all supported formats.

    Args:
        model_path: Path to trained YOLO model (.pt file)
        output_dir: Directory to save exported models
        imgsz: Input image size (default: 640x640)

    Returns:
        Dictionary mapping format name to exported file path

    Example:
        >>> paths = export_all_formats('best.pt', 'exported_models/')
        >>> print(paths['tflite'])  # Path to .tflite file
        >>> print(paths['coreml'])  # Path to .mlpackage
        >>> print(paths['onnx'])    # Path to .onnx file
    """
    results = {}

    try:
        # Export to TFLite (Android/Flutter)
        logger.info("Exporting to TFLite for Android/Flutter...")
        results['tflite'] = export_model_tflite(model_path, output_dir, imgsz)
    except Exception as e:
        logger.error(f"TFLite export failed: {e}")
        results['tflite'] = None

    try:
        # Export to Core ML (iOS)
        logger.info("Exporting to Core ML for iOS...")
        results['coreml'] = export_model_coreml(model_path, output_dir, imgsz)
    except Exception as e:
        logger.error(f"Core ML export failed: {e}")
        results['coreml'] = None

    try:
        # Export to ONNX (Windows/Linux)
        logger.info("Exporting to ONNX for Windows/Linux...")
        results['onnx'] = export_model_onnx(model_path, output_dir, imgsz)
    except Exception as e:
        logger.error(f"ONNX export failed: {e}")
        results['onnx'] = None

    # Original PyTorch model
    results['pytorch'] = model_path

    # Log summary
    logger.info("\n" + "=" * 60)
    logger.info("Model Export Summary:")
    logger.info("=" * 60)
    for platform, path in results.items():
        status = "[OK]" if path else "[FAILED]"
        logger.info(f"{status} {platform:10s}: {path}")
    logger.info("=" * 60)

    return results


# Command-line usage example
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python export.py <model_path> [output_dir] [imgsz]")
        print("Example: python export.py best.pt exported_models/ 640")
        sys.exit(1)

    model_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "exported_models"
    imgsz = int(sys.argv[3]) if len(sys.argv) > 3 else 640

    export_all_formats(model_path, output_dir, imgsz)
