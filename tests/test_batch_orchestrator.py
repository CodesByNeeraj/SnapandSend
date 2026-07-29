import unittest

from src.batch_orchestrator import BatchOrchestrator
from src.notes_curator import CuratedDocument, CuratedNotes
from src.vision_extractor import ExtractedDocument


class FakeVisionExtractor:
    def __init__(self, results):
        self.results = iter(results)
        self.images = []

    async def extractDocument(self, imageBytes):
        self.images.append(imageBytes)
        result = next(self.results)
        if isinstance(result, Exception):
            raise result
        return result


class FakeNotesCurator:
    def __init__(self, result):
        self.result = result
        self.documents = []

    async def curateNotes(self, documents):
        self.documents.append(documents)
        return self.result


class FakeEmailSender:
    def __init__(self):
        self.requests = []

    def sendNotesEmail(self, recipientEmail, notes):
        self.requests.append((recipientEmail, notes))
        return "email-1"


class BatchOrchestratorTests(unittest.IsolatedAsyncioTestCase):
    async def test_process_batch_preserves_image_order_and_sends_one_email(self):
        first = ExtractedDocument("readable", "First", ["One"])
        second = ExtractedDocument("readable", "Second", ["Two"])
        vision = FakeVisionExtractor([first, second])
        curated = CuratedNotes([CuratedDocument("First", ["One"])])
        curator = FakeNotesCurator(curated)
        emailSender = FakeEmailSender()
        orchestrator = BatchOrchestrator(vision, curator, emailSender)

        result = await orchestrator.processBatch(
            "person@example.com", [b"first", b"second"]
        )

        self.assertEqual(result, "email-1")
        self.assertEqual(vision.images, [b"first", b"second"])
        self.assertEqual(curator.documents, [[first, second]])
        self.assertEqual(len(emailSender.requests), 1)

    async def test_process_batch_skips_email_when_curation_is_empty(self):
        vision = FakeVisionExtractor([ExtractedDocument("unreadable", "", [])])
        curator = FakeNotesCurator(CuratedNotes([]))
        emailSender = FakeEmailSender()
        orchestrator = BatchOrchestrator(vision, curator, emailSender)

        result = await orchestrator.processBatch("person@example.com", [b"image"])

        self.assertIsNone(result)
        self.assertEqual(emailSender.requests, [])

    async def test_process_batch_does_not_send_partial_email_after_extraction_failure(self):
        vision = FakeVisionExtractor([RuntimeError("OpenAI failed")])
        curator = FakeNotesCurator(CuratedNotes([]))
        emailSender = FakeEmailSender()
        orchestrator = BatchOrchestrator(vision, curator, emailSender)

        with self.assertRaises(RuntimeError):
            await orchestrator.processBatch("person@example.com", [b"image"])

        self.assertEqual(curator.documents, [])
        self.assertEqual(emailSender.requests, [])


if __name__ == "__main__":
    unittest.main()
