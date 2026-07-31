import unittest

from src.timeout_scheduler import TimeoutScheduler


class FakeExpiredBatchProcessor:
    def __init__(self):
        self.currentTimes = []

    async def processExpiredBatches(self, currentTime):
        self.currentTimes.append(currentTime)
        return 2


class TimeoutSchedulerTests(unittest.IsolatedAsyncioTestCase):
    async def test_process_expired_batches_runs_one_processing_cycle(self):
        processor = FakeExpiredBatchProcessor()
        result = await TimeoutScheduler(processor).processExpiredBatches()
        self.assertEqual(result, 2)
        self.assertEqual(len(processor.currentTimes), 1)


if __name__ == "__main__":
    unittest.main()
