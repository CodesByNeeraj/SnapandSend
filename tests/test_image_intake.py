import unittest

from src.constants import TELEGRAM_MAX_FILE_BYTES
from src.image_intake import (
    FileSizeLimitError,
    UnsupportedImageError,
    downloadImageBytes,
    validateImageUpload,
)


class FakeDownloadedFile:
    def __init__(self, imageBytes: bytes):
        self.imageBytes = imageBytes
        self.downloadCalls = 0

    async def download_as_bytearray(self) -> bytearray:
        self.downloadCalls += 1
        return bytearray(self.imageBytes)


class FakeTelegramFile:
    def __init__(self, downloadedFile: FakeDownloadedFile):
        self.downloadedFile = downloadedFile
        self.getFileCalls = 0

    async def get_file(self) -> FakeDownloadedFile:
        self.getFileCalls += 1
        return self.downloadedFile


class ImageIntakeTests(unittest.IsolatedAsyncioTestCase):
    def test_validate_image_upload_accepts_image_under_limit(self):
        validateImageUpload("image/jpeg", TELEGRAM_MAX_FILE_BYTES)

    def test_validate_image_upload_rejects_non_image_file(self):
        with self.assertRaises(UnsupportedImageError):
            validateImageUpload("application/pdf", 100)

    def test_validate_image_upload_rejects_oversized_file(self):
        with self.assertRaises(FileSizeLimitError):
            validateImageUpload("image/jpeg", TELEGRAM_MAX_FILE_BYTES + 1)

    async def test_download_image_bytes_stays_in_memory(self):
        downloadedFile = FakeDownloadedFile(b"image-bytes")
        telegramFile = FakeTelegramFile(downloadedFile)

        result = await downloadImageBytes(telegramFile)

        self.assertEqual(result, b"image-bytes")
        self.assertEqual(telegramFile.getFileCalls, 1)
        self.assertEqual(downloadedFile.downloadCalls, 1)


if __name__ == "__main__":
    unittest.main()
