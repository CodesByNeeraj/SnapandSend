import unittest

from src.expired_batch_processor import ExpiredBatchProcessor


class FakeBatchManager:
    def closeExpiredBatches(self, currentTime):
        return {"one": [b"first"], "two": [b"second"]}


class FakeUserStore:
    def getEmail(self, userId):
        return f"{userId}@example.com"


class FakeOrchestrator:
    def __init__(self):
        self.requests = []

    async def processBatch(self, email, images):
        self.requests.append((email, images))


class ExpiredBatchProcessorTests(unittest.IsolatedAsyncioTestCase):
    async def test_process_expired_batches_uses_registered_emails(self):
        orchestrator = FakeOrchestrator()
        processor = ExpiredBatchProcessor(
            FakeBatchManager(), FakeUserStore(), orchestrator
        )
        count = await processor.processExpiredBatches("now")
        self.assertEqual(count, 2)
        self.assertEqual(
            orchestrator.requests,
            [("one@example.com", [b"first"]), ("two@example.com", [b"second"])],
        )


if __name__ == "__main__":
    unittest.main()
