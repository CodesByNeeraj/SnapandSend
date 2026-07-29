import json
import unittest

from src.notes_curator import CuratedDocument, CuratedNotes, NotesCurator
from src.notes_curator import NotesCurationError
from src.vision_extractor import ExtractedDocument


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
            {"documents": [{"title": "Project plan", "bullets": ["First milestone"]}]}
        )
        client = FakeClient([FakeResponse(outputText)])
        curator = NotesCurator(client, "gpt-5.6-terra")
        documents = [
            ExtractedDocument(
                status="readable",
                title="Project plan",
                bullets=["First milestone"],
            ),
            ExtractedDocument(
                status="unreadable",
                title="",
                bullets=[],
            ),
            ExtractedDocument(
                status="readable",
                title="Project plan",
                bullets=["First milestone"],
            ),
        ]

        result = await curator.curateNotes(documents)

        self.assertEqual(
            result,
            CuratedNotes(
                documents=[
                    CuratedDocument(
                        title="Project plan",
                        bullets=["First milestone"],
                    )
                ]
            ),
        )
        request = client.responses.calls[0]
        responseFormat = request["text"]["format"]
        self.assertEqual(responseFormat["type"], "json_schema")
        submittedDocuments = json.loads(request["input"][0]["content"][1]["text"])
        self.assertEqual(len(submittedDocuments), 2)

    async def test_curate_notes_returns_empty_result_without_readable_documents(self):
        client = FakeClient([])
        curator = NotesCurator(client, "gpt-5.6-terra")
        documents = [ExtractedDocument(status="unreadable", title="", bullets=[])]

        result = await curator.curateNotes(documents)

        self.assertEqual(result, CuratedNotes(documents=[]))
        self.assertEqual(len(client.responses.calls), 0)

    async def test_curate_notes_retries_once_then_raises(self):
        client = FakeClient([TimeoutError("temporary"), TimeoutError("failed")])
        curator = NotesCurator(client, "gpt-5.6-terra")
        documents = [
            ExtractedDocument(status="readable", title="Title", bullets=["Point"])
        ]

        with self.assertRaises(NotesCurationError):
            await curator.curateNotes(documents)

        self.assertEqual(len(client.responses.calls), 2)

    async def test_curate_notes_rejects_invalid_response_schema(self):
        client = FakeClient(
            [FakeResponse('{"documents":[{"title":"Missing bullets"}]}')]
        )
        curator = NotesCurator(client, "gpt-5.6-terra")
        documents = [
            ExtractedDocument(status="readable", title="Title", bullets=["Point"])
        ]

        with self.assertRaises(NotesCurationError):
            await curator.curateNotes(documents)


if __name__ == "__main__":
    unittest.main()
