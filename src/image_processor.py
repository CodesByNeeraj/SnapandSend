"""Resize and compress uploaded images without writing them to disk."""

import io

from PIL import Image, UnidentifiedImageError

from src.constants import TELEGRAM_MAX_FILE_BYTES

MAX_IMAGE_DIMENSION = 2000
JPEG_QUALITY = 85
INVALID_IMAGE_MESSAGE = "Uploaded bytes are not a valid image"


class ImageProcessingError(ValueError):
    """Raised when uploaded bytes cannot be processed as an image."""


def prepareImage(imageBytes: bytes) -> bytes:
    """Return resized JPEG bytes produced entirely in memory."""

    if len(imageBytes) > TELEGRAM_MAX_FILE_BYTES:
        raise ImageProcessingError("Image exceeds the 20 MB file limit")

    try:
        with Image.open(io.BytesIO(imageBytes)) as sourceImage:
            preparedImage = sourceImage.convert("RGB")
            preparedImage.thumbnail(
                (MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION),
                Image.Resampling.LANCZOS,
            )
            output = io.BytesIO()
            preparedImage.save(output, format="JPEG", quality=JPEG_QUALITY)
            return output.getvalue()
    except (UnidentifiedImageError, OSError) as error:
        raise ImageProcessingError(INVALID_IMAGE_MESSAGE) from error
