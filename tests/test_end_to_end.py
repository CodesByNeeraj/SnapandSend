import unittest
from datetime import datetime, timezone

from src.batch_manager import BatchManager
from src.batch_orchestrator import BatchOrchestrator
from src.done_batch_router import DoneBatchRouter
from src.email_sender import EmailSender
from src.notes_curator import CuratedDocument, CuratedNotes
from src.photo_batch_router import PhotoBatchRouter
from src.rate_limiter import RateLimiter
from src.vision_extractor import ExtractedDocument


class FakeVisionExtractor:
    async def extractDocument(self, imageBytes):
        return ExtractedDocument("readable", "Slide title", ["First point"])


class FailingVisionExtractor:
    async def extractDocument(self, imageBytes):
        raise RuntimeError("OpenAI failed")


class FakeNotesCurator:
    async def curateNotes(self, documents):
        return CuratedNotes([CuratedDocument("Slide title", ["First point"])])


class FakeEmailClient:
    def __init__(self):
        self.requests = []

    def send(self, request):
        self.requests.append(request)
        return {"id": "email-1"}


class FakeUserStore:
    def getEmail(self, userId):
        return "person@example.com"

    def markBatchPending(self, userId):
        pass

    def clearBatchPending(self, userId):
        pass


class EndToEndTests(unittest.IsolatedAsyncioTestCase):
    async def test_clear_image_batch_sends_one_formatted_email(self):
        batchManager = BatchManager()
        photoRouter = PhotoBatchRouter(
            RateLimiter(), batchManager, lambda image: image, FakeUserStore()
        )
        emailClient = FakeEmailClient()
        orchestrator = BatchOrchestrator(
            FakeVisionExtractor(),
            FakeNotesCurator(),
            EmailSender(emailClient, "notes@example.com"),
        )
        doneRouter = DoneBatchRouter(batchManager, FakeUserStore(), orchestrator)

        acknowledgement = photoRouter.acceptImage(
            "user", None, b"image", datetime.now(timezone.utc)
        )
        recipientEmail, images = doneRouter.closeBatchForProcessing("user")
        response = await doneRouter.completeProcessing(recipientEmail, images)

        self.assertIn("1/15", acknowledgement)
        self.assertIn("Email sent", response)
        self.assertEqual(len(emailClient.requests), 1)
        self.assertIn("Slide title", emailClient.requests[0]["text"])

    async def test_eight_image_batch_preserves_order_and_sends_one_email(self):
        batchManager = BatchManager()
        photoRouter = PhotoBatchRouter(
            RateLimiter(), batchManager, lambda image: image, FakeUserStore()
        )
        emailClient = FakeEmailClient()
        orchestrator = BatchOrchestrator(
            FakeVisionExtractor(),
            FakeNotesCurator(),
            EmailSender(emailClient, "notes@example.com"),
        )
        doneRouter = DoneBatchRouter(batchManager, FakeUserStore(), orchestrator)
        now = datetime.now(timezone.utc)

        for index in range(8):
            photoRouter.acceptImage("user", None, bytes([index]), now)

        recipientEmail, images = doneRouter.closeBatchForProcessing("user")
        await doneRouter.completeProcessing(recipientEmail, images)

        self.assertEqual(len(emailClient.requests), 1)

    async def test_sixteenth_image_is_rejected_at_batch_limit(self):
        batchManager = BatchManager()
        photoRouter = PhotoBatchRouter(
            RateLimiter(), batchManager, lambda image: image, FakeUserStore()
        )
        now = datetime.now(timezone.utc)

        for index in range(15):
            photoRouter.acceptImage("user", None, bytes([index]), now)
        response = photoRouter.acceptImage("user", None, b"sixteenth", now)

        self.assertIn("15 photos", response)
        self.assertEqual(len(batchManager.getPhotos("user")), 15)

    async def test_extraction_failure_sends_no_partial_email(self):
        emailClient = FakeEmailClient()
        orchestrator = BatchOrchestrator(
            FailingVisionExtractor(),
            FakeNotesCurator(),
            EmailSender(emailClient, "notes@example.com"),
        )

        with self.assertRaises(RuntimeError):
            await orchestrator.processBatch("person@example.com", [b"image"])

        self.assertEqual(emailClient.requests, [])


if __name__ == "__main__":
    unittest.main()
