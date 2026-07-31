import unittest

from src.batch_manager import EmptyBatchError
from src.done_batch_router import DoneBatchRouter


class FakeBatchManager:
    def __init__(self, images=None):
        self.images = images

    def closeBatch(self, userId):
        if self.images is None:
            raise EmptyBatchError("empty")
        return self.images


class FakeUserStore:
    def getEmail(self, userId):
        return "person@example.com"


class FakeOrchestrator:
    def __init__(self):
        self.requests = []

    async def processBatch(self, email, images):
        self.requests.append((email, images))


class DoneBatchRouterTests(unittest.IsolatedAsyncioTestCase):
    async def test_done_closes_batch_and_uses_registered_email(self):
        orchestrator = FakeOrchestrator()
        router = DoneBatchRouter(
            FakeBatchManager([b"image"]), FakeUserStore(), orchestrator
        )
        response = await router.handleDone("user")
        self.assertIn("being prepared", response)
        self.assertEqual(orchestrator.requests, [("person@example.com", [b"image"])])

    async def test_done_with_no_photos_returns_upload_first_message(self):
        router = DoneBatchRouter(
            FakeBatchManager(), FakeUserStore(), FakeOrchestrator()
        )
        response = await router.handleDone("user")
        self.assertIn("upload", response.lower())


if __name__ == "__main__":
    unittest.main()
