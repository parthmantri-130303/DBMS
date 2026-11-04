import datetime
import os
import uuid
from pathlib import Path

from PIL import Image, ImageOps
from werkzeug.datastructures import FileStorage

from .config import config
from .errors import PayloadTooLargeError, UnsupportedMediaError

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}

def process_and_save_image(file: FileStorage | None) -> str | None:
    """
    Validates, strips EXIF, re-encodes as WebP, and saves to media/YYYY/MM/<uuid>.webp.
    Returns relative URL path (e.g., /media/2026/11/<uuid>.webp).
    """
    if file is None or not file.filename:
        return None

    # Check file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise UnsupportedMediaError(f"Unsupported file extension '{ext}'. Allowed: JPEG, PNG, WebP")

    # Read bytes and check length
    file_bytes = file.read()
    if len(file_bytes) > config.MAX_CONTENT_LENGTH:
        raise PayloadTooLargeError("Image file size exceeds 3 MB limit")

    import io
    try:
        img = Image.open(io.BytesIO(file_bytes))
        # Verify valid image format by reading
        if img.format not in ALLOWED_FORMATS:
            raise UnsupportedMediaError(f"Invalid image format: {img.format}")

        # Correct orientation based on EXIF before stripping
        img = ImageOps.exif_transpose(img)

        # Convert to RGB if needed (e.g. RGBA for webp or CMYK)
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            # Keep alpha channel for WebP
            img = img.convert("RGBA")
        else:
            img = img.convert("RGB")

    except (OSError, SyntaxError):
        raise UnsupportedMediaError("The uploaded file is not a valid image")

    # Generate path: media/YYYY/MM/<uuid>.webp
    now = datetime.datetime.now()
    rel_dir = Path(f"{now.year:04d}") / f"{now.month:02d}"
    target_dir = config.MEDIA_ROOT / rel_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4().hex}.webp"
    file_path = target_dir / filename

    # Save as optimized WebP without EXIF metadata
    img.save(file_path, "WEBP", quality=85, method=6)

    # Return web-accessible URL path
    return f"/media/{now.year:04d}/{now.month:02d}/{filename}"

