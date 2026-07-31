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


class EndToEndTests(unittest.IsolatedAsyncioTestCase):
    async def test_clear_image_batch_sends_one_formatted_email(self):
        batchManager = BatchManager()
        photoRouter = PhotoBatchRouter(RateLimiter(), batchManager, lambda image: image)
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
        response = await doneRouter.handleDone("user")

        self.assertIn("1/15", acknowledgement)
        self.assertIn("being prepared", response)
        self.assertEqual(len(emailClient.requests), 1)
        self.assertIn("Slide title", emailClient.requests[0]["text"])


if __name__ == "__main__":
    unittest.main()
