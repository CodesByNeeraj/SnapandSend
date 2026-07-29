import unittest

from src.vision_extractor import VisionExtractionError, VisionExtractor


class FakeResponses:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


class FakeClient:
    def __init__(self, responses):
        self.responses = FakeResponses(responses)


class FakeResponse:
    def __init__(self, outputText):
        self.output_text = outputText


class VisionExtractorTests(unittest.IsolatedAsyncioTestCase):
    async def test_extract_notes_returns_structured_model_output(self):
        client = FakeClient([FakeResponse("# Slide title\n- Important point")])
        extractor = VisionExtractor(client, "gpt-5.6-terra")

        result = await extractor.extractNotes(b"image-bytes")

        self.assertEqual(result, "# Slide title\n- Important point")
        request = client.responses.calls[0]
        imageContent = request["input"][0]["content"][1]
        imageUrl = imageContent["image_url"]
        self.assertTrue(imageUrl.startswith("data:image/jpeg;base64,"))

    async def test_extract_notes_retries_once_then_raises(self):
        responses = [TimeoutError("temporary"), TimeoutError("failed")]
        client = FakeClient(responses)
        extractor = VisionExtractor(client, "gpt-5.6-terra")

        with self.assertRaises(VisionExtractionError):
            await extractor.extractNotes(b"image-bytes")

        self.assertEqual(len(client.responses.calls), 2)

    async def test_unprocessable_marker_returns_none(self):
        client = FakeClient([FakeResponse("UNPROCESSABLE_IMAGE")])
        extractor = VisionExtractor(client, "gpt-5.6-terra")

        result = await extractor.extractNotes(b"image-bytes")

        self.assertIsNone(result)

    async def test_extract_notes_rejects_output_without_markdown_heading(self):
        client = FakeClient([FakeResponse("- Important point")])
        extractor = VisionExtractor(client, "gpt-5.6-terra")

        with self.assertRaises(VisionExtractionError):
            await extractor.extractNotes(b"image-bytes")

        self.assertEqual(len(client.responses.calls), 1)


if __name__ == "__main__":
    unittest.main()
