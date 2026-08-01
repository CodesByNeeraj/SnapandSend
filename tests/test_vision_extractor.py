import json
import unittest

from src.vision_extractor import ContentBlock, ExtractedDocument, VisionExtractionError
from src.vision_extractor import FlowchartEdge, VisionExtractor


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
    async def test_extract_document_returns_bullets_block(self):
        outputText = json.dumps(
            {
                "status": "readable",
                "title": "Slide title",
                "blocks": [{"type": "bullets", "items": ["Important point"]}],
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
                blocks=[ContentBlock(type="bullets", items=["Important point"])],
            ),
        )
        request = client.responses.calls[0]
        imageContent = request["input"][0]["content"][1]
        imageUrl = imageContent["image_url"]
        self.assertTrue(imageUrl.startswith("data:image/jpeg;base64,"))
        responseFormat = request["text"]["format"]
        self.assertEqual(responseFormat["type"], "json_schema")
        self.assertTrue(responseFormat["strict"])

    async def test_extract_document_returns_paragraph_block(self):
        outputText = json.dumps(
            {
                "status": "readable",
                "title": "Whiteboard note",
                "blocks": [{"type": "paragraph", "text": "Some free-form prose."}],
            }
        )
        client = FakeClient([FakeResponse(outputText)])
        extractor = VisionExtractor(client, "gpt-5.6-terra")

        result = await extractor.extractDocument(b"image-bytes")

        self.assertEqual(
            result.blocks,
            [ContentBlock(type="paragraph", text="Some free-form prose.")],
        )

    async def test_extract_document_returns_mixed_blocks_in_order(self):
        outputText = json.dumps(
            {
                "status": "readable",
                "title": "Mixed slide",
                "blocks": [
                    {"type": "paragraph", "text": "Intro paragraph."},
                    {"type": "bullets", "items": ["First", "Second"]},
                ],
            }
        )
        client = FakeClient([FakeResponse(outputText)])
        extractor = VisionExtractor(client, "gpt-5.6-terra")

        result = await extractor.extractDocument(b"image-bytes")

        self.assertEqual(
            result.blocks,
            [
                ContentBlock(type="paragraph", text="Intro paragraph."),
                ContentBlock(type="bullets", items=["First", "Second"]),
            ],
        )

    async def test_extract_notes_retries_once_then_raises(self):
        responses = [TimeoutError("temporary"), TimeoutError("failed")]
        client = FakeClient(responses)
        extractor = VisionExtractor(client, "gpt-5.6-terra")

        with self.assertRaises(VisionExtractionError):
            await extractor.extractDocument(b"image-bytes")

        self.assertEqual(len(client.responses.calls), 2)

    async def test_extract_document_marks_unreadable_image(self):
        unreadableDocument = dict(status="unreadable", title="", blocks=[])
        outputText = json.dumps(unreadableDocument)
        client = FakeClient([FakeResponse(outputText)])
        extractor = VisionExtractor(client, "gpt-5.6-terra")

        result = await extractor.extractDocument(b"image-bytes")

        self.assertEqual(
            result,
            ExtractedDocument(status="unreadable", title="", blocks=[]),
        )

    async def test_extract_document_rejects_invalid_response_schema(self):
        client = FakeClient([FakeResponse('{"status":"readable"}')])
        extractor = VisionExtractor(client, "gpt-5.6-terra")

        with self.assertRaises(VisionExtractionError):
            await extractor.extractDocument(b"image-bytes")

        self.assertEqual(len(client.responses.calls), 1)

    async def test_extract_document_returns_flowchart_block(self):
        outputText = json.dumps(
            {
                "status": "readable",
                "title": "Deploy process",
                "blocks": [
                    {
                        "type": "flowchart",
                        "nodes": ["Start", "Run tests", "Deploy"],
                        "edges": [
                            {"source": "Start", "target": "Run tests", "label": ""},
                            {"source": "Run tests", "target": "Deploy", "label": ""},
                        ],
                    }
                ],
            }
        )
        client = FakeClient([FakeResponse(outputText)])
        extractor = VisionExtractor(client, "gpt-5.6-terra")

        result = await extractor.extractDocument(b"image-bytes")

        self.assertEqual(
            result.blocks,
            [
                ContentBlock(
                    type="flowchart",
                    nodes=["Start", "Run tests", "Deploy"],
                    edges=[
                        FlowchartEdge(source="Start", target="Run tests", label=""),
                        FlowchartEdge(source="Run tests", target="Deploy", label=""),
                    ],
                )
            ],
        )

    async def test_extract_document_returns_branching_flowchart_with_labels(self):
        outputText = json.dumps(
            {
                "status": "readable",
                "title": "Approval process",
                "blocks": [
                    {
                        "type": "flowchart",
                        "nodes": ["Submit", "Review", "Approve", "Reject"],
                        "edges": [
                            {"source": "Submit", "target": "Review", "label": ""},
                            {
                                "source": "Review",
                                "target": "Approve",
                                "label": "yes",
                            },
                            {"source": "Review", "target": "Reject", "label": "no"},
                        ],
                    }
                ],
            }
        )
        client = FakeClient([FakeResponse(outputText)])
        extractor = VisionExtractor(client, "gpt-5.6-terra")

        result = await extractor.extractDocument(b"image-bytes")

        block = result.blocks[0]
        self.assertEqual(block.type, "flowchart")
        self.assertEqual(
            block.edges[1],
            FlowchartEdge(source="Review", target="Approve", label="yes"),
        )

    async def test_extract_document_rejects_flowchart_missing_edges(self):
        outputText = json.dumps(
            {
                "status": "readable",
                "title": "Broken diagram",
                "blocks": [{"type": "flowchart", "nodes": ["A", "B"]}],
            }
        )
        client = FakeClient([FakeResponse(outputText)])
        extractor = VisionExtractor(client, "gpt-5.6-terra")

        with self.assertRaises(VisionExtractionError):
            await extractor.extractDocument(b"image-bytes")

    async def test_extract_document_rejects_block_with_unknown_type(self):
        outputText = json.dumps(
            {
                "status": "readable",
                "title": "Slide title",
                "blocks": [{"type": "table", "items": ["a"]}],
            }
        )
        client = FakeClient([FakeResponse(outputText)])
        extractor = VisionExtractor(client, "gpt-5.6-terra")

        with self.assertRaises(VisionExtractionError):
            await extractor.extractDocument(b"image-bytes")


if __name__ == "__main__":
    unittest.main()
