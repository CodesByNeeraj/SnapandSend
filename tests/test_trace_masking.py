import unittest

from src.trace_masking import REDACTED_IMAGE_PLACEHOLDER, maskImageData


class MaskImageDataTests(unittest.TestCase):
    def test_redacts_base64_image_data_url_in_a_string(self):
        text = "before data:image/jpeg;base64,QUJDREVGRw== after"

        masked = maskImageData(data=text)

        self.assertNotIn("QUJDREVGRw==", masked)
        self.assertIn(REDACTED_IMAGE_PLACEHOLDER, masked)
        self.assertIn("before", masked)
        self.assertIn("after", masked)

    def test_leaves_plain_text_untouched(self):
        text = "Slide title\n- point one\n- point two"

        self.assertEqual(maskImageData(data=text), text)

    def test_redacts_image_data_nested_inside_dicts_and_lists(self):
        payload = {
            "messages": [
                {
                    "content": [
                        {"type": "text", "text": "extract this"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "data:image/png;base64,ZmFrZS1pbWFnZS1ieXRlcw=="
                            },
                        },
                    ]
                }
            ]
        }

        masked = maskImageData(data=payload)

        maskedUrl = masked["messages"][0]["content"][1]["image_url"]["url"]
        self.assertEqual(maskedUrl, REDACTED_IMAGE_PLACEHOLDER)
        self.assertEqual(masked["messages"][0]["content"][0]["text"], "extract this")

    def test_passes_through_non_string_scalars(self):
        self.assertEqual(maskImageData(data=42), 42)
        self.assertIsNone(maskImageData(data=None))


if __name__ == "__main__":
    unittest.main()
