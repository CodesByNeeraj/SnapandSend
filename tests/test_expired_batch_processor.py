import unittest

from src.expired_batch_processor import ExpiredBatchProcessor


class FakeBatchManager:
    def closeExpiredBatches(self, currentTime):
        return {"one": [b"first"], "two": [b"second"], "three": [b"third"]}


class FakeUserStore:
    def __init__(self):
        self.pendingClears = []

    def getEmail(self, userId):
        return None if userId == "three" else f"{userId}@example.com"

    def clearBatchPending(self, userId):
        self.pendingClears.append(userId)


class ExpiredBatchProcessorTests(unittest.TestCase):
    def test_returns_recipient_and_images_only_for_users_with_a_registered_email(self):
        userStore = FakeUserStore()
        processor = ExpiredBatchProcessor(FakeBatchManager(), userStore)

        ready = processor.closeExpiredBatchesForProcessing("now")

        self.assertEqual(
            ready,
            [
                ("one", "one@example.com", [b"first"]),
                ("two", "two@example.com", [b"second"]),
            ],
        )

    def test_clears_the_pending_flag_for_every_expired_user_including_no_email(self):
        userStore = FakeUserStore()
        processor = ExpiredBatchProcessor(FakeBatchManager(), userStore)

        processor.closeExpiredBatchesForProcessing("now")

        self.assertEqual(userStore.pendingClears, ["one", "two", "three"])


if __name__ == "__main__":
    unittest.main()
