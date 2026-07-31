import unittest
from datetime import datetime, timezone

from src.photo_batch_router import PhotoBatchRouter


class FakeRateLimiter:
    def __init__(self, accepts=True):
        self.accepts = accepts
        self.recorded = 0

    def getCalendarDay(self, receivedAt):
        return receivedAt.date()

    def canAcceptPhoto(self, userId, calendarDay, userName):
        return self.accepts

    def recordPhoto(self, userId, calendarDay, userName):
        self.recorded += 1


class FakeBatchManager:
    def __init__(self, count=1, fails=False):
        self.count = count
        self.fails = fails
        self.images = []

    def addPhoto(self, userId, imageBytes, receivedAt):
        if self.fails:
            raise ValueError()
        self.images.append(imageBytes)
        return self.count


class FakeUserStore:
    def __init__(self):
        self.pendingMarks = []

    def markBatchPending(self, userId):
        self.pendingMarks.append(userId)


class PhotoBatchRouterTests(unittest.TestCase):
    def test_accept_image_prepares_stores_and_acknowledges(self):
        rateLimiter = FakeRateLimiter()
        batchManager = FakeBatchManager(count=2)
        userStore = FakeUserStore()
        router = PhotoBatchRouter(
            rateLimiter, batchManager, lambda image: b"prepared", userStore
        )
        result = router.acceptImage("user", None, b"raw", datetime.now(timezone.utc))
        self.assertIn("2/15", result)
        self.assertEqual(batchManager.images, [b"prepared"])
        self.assertEqual(rateLimiter.recorded, 1)

    def test_accept_image_does_not_prepare_or_record_when_rate_limited(self):
        rateLimiter = FakeRateLimiter(accepts=False)
        batchManager = FakeBatchManager()
        userStore = FakeUserStore()
        router = PhotoBatchRouter(
            rateLimiter, batchManager, lambda image: b"prepared", userStore
        )
        result = router.acceptImage("user", None, b"raw", datetime.now(timezone.utc))
        self.assertIn("limit", result)
        self.assertEqual(batchManager.images, [])
        self.assertEqual(rateLimiter.recorded, 0)
        self.assertEqual(userStore.pendingMarks, [])

    def test_accept_image_marks_pending_batch_only_for_first_photo(self):
        rateLimiter = FakeRateLimiter()
        userStore = FakeUserStore()
        firstPhotoRouter = PhotoBatchRouter(
            rateLimiter, FakeBatchManager(count=1), lambda image: b"prepared", userStore
        )
        firstPhotoRouter.acceptImage("user", None, b"raw", datetime.now(timezone.utc))
        self.assertEqual(userStore.pendingMarks, ["user"])

        laterPhotoRouter = PhotoBatchRouter(
            rateLimiter, FakeBatchManager(count=2), lambda image: b"prepared", userStore
        )
        laterPhotoRouter.acceptImage("user", None, b"raw", datetime.now(timezone.utc))
        self.assertEqual(userStore.pendingMarks, ["user"])


if __name__ == "__main__":
    unittest.main()
