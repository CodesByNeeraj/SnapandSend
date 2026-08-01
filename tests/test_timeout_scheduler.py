import unittest

from src.timeout_scheduler import TimeoutScheduler


class FakeExpiredBatchProcessor:
    def __init__(self):
        self.currentTimes = []

    def closeExpiredBatchesForProcessing(self, currentTime):
        self.currentTimes.append(currentTime)
        return [("user", "user@example.com", [b"image"])]


class TimeoutSchedulerTests(unittest.TestCase):
    def test_get_expired_batches_for_processing_runs_one_cycle(self):
        processor = FakeExpiredBatchProcessor()
        result = TimeoutScheduler(processor).getExpiredBatchesForProcessing()
        self.assertEqual(result, [("user", "user@example.com", [b"image"])])
        self.assertEqual(len(processor.currentTimes), 1)


if __name__ == "__main__":
    unittest.main()
