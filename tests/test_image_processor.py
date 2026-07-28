import io
import unittest
from unittest.mock import patch

from PIL import Image

from src.constants import TELEGRAM_MAX_FILE_BYTES
from src.image_processor import ImageProcessingError, prepareImage


class ImageProcessorTests(unittest.TestCase):
    def test_prepare_image_resizes_and_returns_jpeg_bytes(self):
        source = Image.new("RGB", (4000, 2000), "white")
        sourceBytes = io.BytesIO()
        source.save(sourceBytes, format="PNG")

        preparedBytes = prepareImage(sourceBytes.getvalue())

        preparedImage = Image.open(io.BytesIO(preparedBytes))
        self.assertEqual(preparedImage.format, "JPEG")
        self.assertLessEqual(max(preparedImage.size), 2000)

    def test_prepare_image_rejects_invalid_bytes(self):
        with self.assertRaises(ImageProcessingError):
            prepareImage(b"not an image")

    def test_prepare_image_rejects_oversized_files_before_decoding(self):
        oversizedBytes = b"x" * (TELEGRAM_MAX_FILE_BYTES + 1)

        with patch("src.image_processor.Image.open") as openImage:
            with self.assertRaises(ImageProcessingError):
                prepareImage(oversizedBytes)

        openImage.assert_not_called()


if __name__ == "__main__":
    unittest.main()
