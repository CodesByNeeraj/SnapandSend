import unittest

from src.batch_manager import EmptyBatchError
from src.done_batch_router import (
    EMAIL_SENT_MESSAGE,
    EMPTY_BATCH_MESSAGE,
    UNREADABLE_BATCH_MESSAGE,
    DoneBatchRouter,
    NoBatchToProcessError,
)


class FakeBatchManager:
    def __init__(self, images=None):
        self.images = images

    def closeBatch(self, userId):
        if self.images is None:
            raise EmptyBatchError("empty")
        return self.images


class FakeUserStore:
    def __init__(self, email="person@example.com"):
        self.email = email
        self.pendingClears = []
        self.usageCounts = {}

    def getEmail(self, userId):
        return self.email

    def clearBatchPending(self, userId):
        self.pendingClears.append(userId)

    def incrementUsageCount(self, userId):
        self.usageCounts[userId] = self.usageCounts.get(userId, 0) + 1
        return self.usageCounts[userId]


class FakeOrchestrator:
    def __init__(self):
        self.requests = []

    async def processBatch(self, email, images):
        self.requests.append((email, images))
        return "email-1"


class EmptyNotesOrchestrator(FakeOrchestrator):
    async def processBatch(self, email, images):
        self.requests.append((email, images))
        return None


class CloseBatchForProcessingTests(unittest.TestCase):
    def test_returns_recipient_email_and_images_for_a_closable_batch(self):
        userStore = FakeUserStore()
        router = DoneBatchRouter(FakeBatchManager([b"image"]), userStore, None)

        recipientEmail, images = router.closeBatchForProcessing("user")

        self.assertEqual(recipientEmail, "person@example.com")
        self.assertEqual(images, [b"image"])
        self.assertEqual(userStore.pendingClears, ["user"])

    def test_raises_when_batch_is_empty(self):
        userStore = FakeUserStore()
        router = DoneBatchRouter(FakeBatchManager(), userStore, None)

        with self.assertRaises(NoBatchToProcessError):
            router.closeBatchForProcessing("user")
        self.assertEqual(userStore.pendingClears, [])

    def test_raises_when_no_email_is_registered(self):
        userStore = FakeUserStore(email=None)
        router = DoneBatchRouter(FakeBatchManager([b"image"]), userStore, None)

        with self.assertRaises(NoBatchToProcessError):
            router.closeBatchForProcessing("user")


class CompleteProcessingTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_email_sent_message_and_usage_count_on_success(self):
        orchestrator = FakeOrchestrator()
        userStore = FakeUserStore()
        router = DoneBatchRouter(None, userStore, orchestrator)

        response, usageCount = await router.completeProcessing(
            "person@example.com", [b"image"], "user"
        )

        self.assertEqual(response, EMAIL_SENT_MESSAGE)
        self.assertEqual(usageCount, 1)
        self.assertEqual(orchestrator.requests, [("person@example.com", [b"image"])])

    async def test_returns_unreadable_batch_message_and_no_usage_count(self):
        userStore = FakeUserStore()
        router = DoneBatchRouter(None, userStore, EmptyNotesOrchestrator())

        response, usageCount = await router.completeProcessing(
            "person@example.com", [b"image"], "user"
        )

        self.assertEqual(response, UNREADABLE_BATCH_MESSAGE)
        self.assertIsNone(usageCount)
        self.assertEqual(userStore.usageCounts, {})


class MessageConstantTests(unittest.TestCase):
    def test_empty_batch_message_mentions_upload(self):
        self.assertIn("upload", EMPTY_BATCH_MESSAGE.lower())

    def test_unreadable_batch_message_mentions_readable_text(self):
        self.assertIn("readable text", UNREADABLE_BATCH_MESSAGE.lower())


if __name__ == "__main__":
    unittest.main()
