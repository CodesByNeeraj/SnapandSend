import unittest
from datetime import datetime, timedelta, timezone

from src.batch_manager import BatchManager, EmptyBatchError, BatchLimitError
from src.constants import MAX_BATCH_PHOTOS


class BatchManagerTests(unittest.TestCase):
    def setUp(self):
        self.manager = BatchManager()
        self.start = datetime(2026, 7, 28, 10, 0, tzinfo=timezone.utc)

    def test_photos_are_kept_in_arrival_order_and_counted(self):
        firstCount = self.manager.addPhoto("user-1", b"first", self.start)
        secondCount = self.manager.addPhoto(
            "user-1", b"second", self.start + timedelta(seconds=10)
        )

        self.assertEqual(firstCount, 1)
        self.assertEqual(secondCount, 2)
        photos = self.manager.getPhotos("user-1")
        self.assertEqual(photos, [b"first", b"second"])

    def test_batch_expires_three_minutes_after_latest_photo(self):
        photoTime = self.start
        self.manager.addPhoto("user-1", b"photo", photoTime)

        expiredUsers = self.manager.getExpiredUserIds(
            photoTime + timedelta(seconds=179)
        )
        self.assertEqual(expiredUsers, [])
        self.assertEqual(
            self.manager.getExpiredUserIds(photoTime + timedelta(seconds=180)),
            ["user-1"],
        )

    def test_close_expired_batches_preserves_active_batch(self):
        self.manager.addPhoto("expired-user", b"expired", self.start)
        self.manager.addPhoto(
            "active-user", b"active", self.start + timedelta(seconds=1)
        )

        closedBatches = self.manager.closeExpiredBatches(
            self.start + timedelta(seconds=180)
        )

        self.assertEqual(closedBatches, {"expired-user": [b"expired"]})
        self.assertEqual(self.manager.getPhotos("expired-user"), [])
        self.assertEqual(self.manager.getPhotos("active-user"), [b"active"])

    def test_close_batch_returns_photos_and_clears_state(self):
        self.manager.addPhoto("user-1", b"photo", self.start)

        photos = self.manager.closeBatch("user-1")

        self.assertEqual(photos, [b"photo"])
        with self.assertRaises(EmptyBatchError):
            self.manager.closeBatch("user-1")

    def test_batch_rejects_photo_above_maximum(self):
        for photoNumber in range(MAX_BATCH_PHOTOS):
            count = self.manager.addPhoto(
                "user-1", f"photo-{photoNumber}".encode(), self.start
            )

        self.assertEqual(count, MAX_BATCH_PHOTOS)
        with self.assertRaises(BatchLimitError):
            self.manager.addPhoto("user-1", b"too-many", self.start)

        photos = self.manager.getPhotos("user-1")
        self.assertEqual(len(photos), MAX_BATCH_PHOTOS)


if __name__ == "__main__":
    unittest.main()
