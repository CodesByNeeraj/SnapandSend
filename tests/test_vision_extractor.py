import json
import unittest

from src.vision_extractor import ExtractedDocument, VisionExtractionError
from src.vision_extractor import VisionExtractor


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
    async def test_extract_document_returns_typed_content(self):
        outputText = json.dumps(
            {
                "status": "readable",
                "title": "Slide title",
                "bullets": ["Important point"],
            }
        )
        client = FakeClient([FakeResponse(outputText)])
        extractor = VisionExtractor(client, "gpt-5.6-terra")

        result = await extractor.extractDocument(b"image-bytes")

        self.assertEqual(
            result,
            ExtractedDocument(
                status="readable",
                title="Slide title",
                bullets=["Important point"],
            ),
        )
        request = client.responses.calls[0]
        imageContent = request["input"][0]["content"][1]
        imageUrl = imageContent["image_url"]
        self.assertTrue(imageUrl.startswith("data:image/jpeg;base64,"))
        responseFormat = request["text"]["format"]
        self.assertEqual(responseFormat["type"], "json_schema")
        self.assertTrue(responseFormat["strict"])

    async def test_extract_notes_retries_once_then_raises(self):
        responses = [TimeoutError("temporary"), TimeoutError("failed")]
        client = FakeClient(responses)
        extractor = VisionExtractor(client, "gpt-5.6-terra")

        with self.assertRaises(VisionExtractionError):
            await extractor.extractDocument(b"image-bytes")

        self.assertEqual(len(client.responses.calls), 2)

    async def test_extract_document_marks_unreadable_image(self):
        outputText = json.dumps(
            {"status": "unreadable", "title": "", "bullets": []}
        )
        client = FakeClient([FakeResponse(outputText)])
        extractor = VisionExtractor(client, "gpt-5.6-terra")

        result = await extractor.extractDocument(b"image-bytes")

        self.assertEqual(
            result,
            ExtractedDocument(status="unreadable", title="", bullets=[]),
        )

    async def test_extract_document_rejects_invalid_response_schema(self):
        client = FakeClient([FakeResponse('{"status":"readable"}')])
        extractor = VisionExtractor(client, "gpt-5.6-terra")

        with self.assertRaises(VisionExtractionError):
            await extractor.extractDocument(b"image-bytes")

        self.assertEqual(len(client.responses.calls), 1)


if __name__ == "__main__":
    unittest.main()
