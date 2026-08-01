import json
import unittest

from src.notes_curator import CuratedDocument, CuratedNotes, NotesCurator
from src.notes_curator import NotesCurationError
from src.vision_extractor import ContentBlock, ExtractedDocument


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


class NotesCuratorTests(unittest.IsolatedAsyncioTestCase):
    async def test_curate_notes_omits_unreadable_and_duplicate_documents(self):
        outputText = json.dumps(
            {
                "documents": [
                    {
                        "title": "Project plan",
                        "blocks": [{"type": "bullets", "items": ["First milestone"]}],
                    }
                ]
            }
        )
        client = FakeClient([FakeResponse(outputText)])
        curator = NotesCurator(client, "gpt-5.6-terra")
        bulletsBlock = [ContentBlock(type="bullets", items=["First milestone"])]
        documents = [
            ExtractedDocument(
                status="readable", title="Project plan", blocks=bulletsBlock
            ),
            ExtractedDocument(status="unreadable", title="", blocks=[]),
            ExtractedDocument(
                status="readable", title="Project plan", blocks=bulletsBlock
            ),
        ]

        result = await curator.curateNotes(documents)

        self.assertEqual(
            result,
            CuratedNotes(
                documents=[CuratedDocument(title="Project plan", blocks=bulletsBlock)]
            ),
        )
        request = client.responses.calls[0]
        responseFormat = request["text"]["format"]
        self.assertEqual(responseFormat["type"], "json_schema")
        submittedDocuments = json.loads(request["input"][0]["content"][1]["text"])
        self.assertEqual(len(submittedDocuments), 2)

    async def test_curate_notes_preserves_paragraph_blocks(self):
        outputText = json.dumps(
            {
                "documents": [
                    {
                        "title": "Whiteboard",
                        "blocks": [{"type": "paragraph", "text": "Free-form notes."}],
                    }
                ]
            }
        )
        client = FakeClient([FakeResponse(outputText)])
        curator = NotesCurator(client, "gpt-5.6-terra")
        documents = [
            ExtractedDocument(
                status="readable",
                title="Whiteboard",
                blocks=[ContentBlock(type="paragraph", text="Free-form notes.")],
            )
        ]

        result = await curator.curateNotes(documents)

        self.assertEqual(
            result.documents[0].blocks,
            [ContentBlock(type="paragraph", text="Free-form notes.")],
        )

    async def test_curate_notes_returns_empty_result_without_readable_documents(self):
        client = FakeClient([])
        curator = NotesCurator(client, "gpt-5.6-terra")
        documents = [ExtractedDocument(status="unreadable", title="", blocks=[])]

        result = await curator.curateNotes(documents)

        self.assertEqual(result, CuratedNotes(documents=[]))
        self.assertEqual(len(client.responses.calls), 0)

    async def test_curate_notes_retries_once_then_raises(self):
        client = FakeClient([TimeoutError("temporary"), TimeoutError("failed")])
        curator = NotesCurator(client, "gpt-5.6-terra")
        documents = [
            ExtractedDocument(
                status="readable",
                title="Title",
                blocks=[ContentBlock(type="bullets", items=["Point"])],
            )
        ]

        with self.assertRaises(NotesCurationError):
            await curator.curateNotes(documents)

        self.assertEqual(len(client.responses.calls), 2)

    async def test_curate_notes_rejects_invalid_response_schema(self):
        client = FakeClient(
            [FakeResponse('{"documents":[{"title":"Missing blocks"}]}')]
        )
        curator = NotesCurator(client, "gpt-5.6-terra")
        documents = [
            ExtractedDocument(
                status="readable",
                title="Title",
                blocks=[ContentBlock(type="bullets", items=["Point"])],
            )
        ]

        with self.assertRaises(NotesCurationError):
            await curator.curateNotes(documents)


if __name__ == "__main__":
    unittest.main()
