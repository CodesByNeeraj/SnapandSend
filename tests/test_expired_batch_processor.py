import unittest

from src.expired_batch_processor import ExpiredBatchProcessor


class FakeBatchManager:
    def closeExpiredBatches(self, currentTime):
        return {"one": [b"first"], "two": [b"second"]}


class FakeUserStore:
    def __init__(self):
        self.pendingClears = []

    def getEmail(self, userId):
        return f"{userId}@example.com"

    def clearBatchPending(self, userId):
        self.pendingClears.append(userId)


class FakeOrchestrator:
    def __init__(self):
        self.requests = []

    async def processBatch(self, email, images):
        self.requests.append((email, images))


class ExpiredBatchProcessorTests(unittest.IsolatedAsyncioTestCase):
    async def test_process_expired_batches_uses_registered_emails(self):
        orchestrator = FakeOrchestrator()
        userStore = FakeUserStore()
        processor = ExpiredBatchProcessor(FakeBatchManager(), userStore, orchestrator)
        count = await processor.processExpiredBatches("now")
        self.assertEqual(count, 2)
        self.assertEqual(
            orchestrator.requests,
            [("one@example.com", [b"first"]), ("two@example.com", [b"second"])],
        )
        self.assertEqual(userStore.pendingClears, ["one", "two"])


if __name__ == "__main__":
    unittest.main()
