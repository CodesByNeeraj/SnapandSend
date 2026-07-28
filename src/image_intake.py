"""Validate and download Telegram image uploads in memory."""

from typing import Any

from src.constants import TELEGRAM_MAX_FILE_BYTES

IMAGE_MIME_PREFIX = "image/"
UNSUPPORTED_IMAGE_MESSAGE = "Only image files are supported"
OVERSIZED_IMAGE_MESSAGE = "Image exceeds the 20 MB file limit"


class UnsupportedImageError(ValueError):
    """Raised when an upload is not an image file."""


class FileSizeLimitError(ValueError):
    """Raised when an image exceeds Telegram's supported file size."""


def validateImageUpload(mimeType: str | None, fileSize: int) -> None:
    """Validate the image MIME type and Telegram file-size limit."""

    if not mimeType or not mimeType.startswith(IMAGE_MIME_PREFIX):
        raise UnsupportedImageError(UNSUPPORTED_IMAGE_MESSAGE)
    if fileSize > TELEGRAM_MAX_FILE_BYTES:
        raise FileSizeLimitError(OVERSIZED_IMAGE_MESSAGE)


async def downloadImageBytes(telegramFile: Any) -> bytes:
    """Download Telegram image bytes without writing them to disk."""

    downloadedFile = await telegramFile.get_file()
    return bytes(await downloadedFile.download_as_bytearray())
