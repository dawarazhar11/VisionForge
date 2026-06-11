"""
Render preview generation — draws YOLO label boxes onto rendered images.

Previews are written to <dataset_dir>/previews/ after a render job so
users can visually verify the auto-generated annotations.
"""
from pathlib import Path
from typing import List, Optional, Union

from loguru import logger
from PIL import Image, ImageDraw

PREVIEW_DIR_NAME = "previews"

_COLORS = [
    "#FF3838", "#48F90A", "#00C2FF", "#FFB21D",
    "#CB38FF", "#FF701F", "#3DDB86", "#6473FF",
]


def generate_render_previews(
    dataset_dir: Union[str, Path],
    class_names: Optional[List[str]] = None,
    max_images: Optional[int] = None,
) -> int:
    """
    Draw YOLO boxes from each render_XXXX.txt onto its render_XXXX.png.

    Annotated copies are saved under <dataset_dir>/previews/ with the same
    filenames. Images without a label file are copied unannotated so the
    preview set always mirrors the dataset.

    Returns:
        Number of preview images written.
    """
    dataset_dir = Path(dataset_dir)
    out_dir = dataset_dir / PREVIEW_DIR_NAME
    out_dir.mkdir(parents=True, exist_ok=True)

    images = sorted(dataset_dir.glob("*.png"))
    if max_images is not None:
        images = images[:max_images]

    count = 0
    for png in images:
        try:
            img = Image.open(png).convert("RGB")
            draw = ImageDraw.Draw(img)
            width, height = img.size

            label_path = png.with_suffix(".txt")
            if label_path.exists():
                for line in label_path.read_text().splitlines():
                    parts = line.split()
                    if len(parts) < 5:
                        continue
                    cls = int(parts[0])
                    xc, yc, w, h = (float(v) for v in parts[1:5])
                    x0, y0 = (xc - w / 2) * width, (yc - h / 2) * height
                    x1, y1 = (xc + w / 2) * width, (yc + h / 2) * height
                    color = _COLORS[cls % len(_COLORS)]
                    if class_names and cls < len(class_names):
                        name = class_names[cls]
                    else:
                        name = f"class {cls}"
                    draw.rectangle([x0, y0, x1, y1], outline=color, width=3)
                    draw.text((x0 + 4, y0 + 4), name, fill=color)

            img.save(out_dir / png.name)
            count += 1
        except Exception as exc:
            logger.warning(f"Preview generation failed for {png.name}: {exc}")

    logger.info(f"Generated {count} preview images in {out_dir}")
    return count
