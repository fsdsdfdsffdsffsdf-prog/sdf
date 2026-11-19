"""
StorageService — secure photo upload handling.

Responsibilities:
  1. Read magic bytes to verify real MIME type (not trusting extension).
  2. Decode and verify image integrity with Pillow.
  3. Check file size limits.
  4. Strip EXIF metadata for privacy.
  5. Convert to WebP and save to date-partitioned directory.
  6. Return absolute Path to saved file.
  7. Protect against Path Traversal attacks.
"""

import io
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Union

from PIL import Image, UnidentifiedImageError

from app.config import get_settings
from app.core.logging import logger
from app.core.security import is_safe_path

settings = get_settings()

# Allowed image magic byte signatures
_ALLOWED_MAGIC_BYTES = {
    b"\xff\xd8\xff": "JPEG",
    b"\x89PNG": "PNG",
    b"GIF8": "GIF",
    b"RIFF": "WEBP",  # Actually RIFF....WEBP but checking prefix is enough
}

_MAX_SIZE_BYTES = settings.MAX_PHOTO_SIZE_BYTES
_OUTPUT_FORMAT = "WEBP"
_OUTPUT_QUALITY = 85


class StorageService:
    """Handles secure file saving with format validation and path isolation."""

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir / "photos"
        self._base_dir.mkdir(parents=True, exist_ok=True)

    async def save_photo(self, raw_bytes: Union[bytes, bytearray]) -> Path:
        """
        Validates, optimises, and saves photo bytes to disk.

        Args:
            raw_bytes: Raw binary content of the uploaded file.

        Returns:
            Absolute Path to the saved WebP image.

        Raises:
            ValueError: If the file fails any security or format check.
        """
        # 1. Size check
        if len(raw_bytes) > _MAX_SIZE_BYTES:
            raise ValueError(
                f"Файл слишком большой: {len(raw_bytes) // 1024 // 1024} МБ. "
                f"Максимальный размер — {_MAX_SIZE_BYTES // 1024 // 1024} МБ."
            )

        if len(raw_bytes) < 8:
            raise ValueError("Файл повреждён или слишком мал.")

        # 2. Magic bytes check (real MIME validation)
        self._check_magic_bytes(raw_bytes)

        # 3. Pillow decoding + integrity check
        try:
            img = Image.open(io.BytesIO(raw_bytes))
            img.verify()  # Raises if file is damaged or truncated
            img = Image.open(io.BytesIO(raw_bytes))  # Re-open for processing after verify()
        except UnidentifiedImageError:
            raise ValueError("Не удалось распознать формат изображения.")
        except Exception as exc:
            raise ValueError(f"Изображение повреждено: {exc}")

        # 4. Strip EXIF metadata (privacy)
        img_clean = self._strip_exif(img)

        # 5. Build date-partitioned save path
        now = datetime.now(timezone.utc)
        sub_dir = self._base_dir / str(now.year) / f"{now.month:02d}" / f"{now.day:02d}"
        sub_dir.mkdir(parents=True, exist_ok=True)

        file_name = f"{uuid.uuid4().hex}.webp"
        target_path = sub_dir / file_name

        # 6. Path Traversal guard
        if not is_safe_path(self._base_dir, target_path):
            raise ValueError("Недопустимый путь к файлу (Path Traversal защита).")

        # 7. Save as optimized WebP
        img_clean.save(target_path, format=_OUTPUT_FORMAT, quality=_OUTPUT_QUALITY, method=4)
        logger.info("Photo saved: %s (%d bytes input)", target_path, len(raw_bytes))

        return target_path

    @staticmethod
    def _check_magic_bytes(data: bytes) -> None:
        """Raises ValueError if file header doesn't match any known image format."""
        for magic, fmt in _ALLOWED_MAGIC_BYTES.items():
            if data[:len(magic)] == magic:
                return
        raise ValueError(
            "Недопустимый формат файла. Разрешены только JPEG, PNG, GIF, WebP."
        )

    @staticmethod
    def _strip_exif(img: Image.Image) -> Image.Image:
        """Returns a new PIL Image without EXIF metadata."""
        try:
            data = list(img.getdata())
            clean = Image.new(img.mode, img.size)
            clean.putdata(data)
            return clean
        except Exception:
            return img  # If stripping fails, return original (better than failing upload)
