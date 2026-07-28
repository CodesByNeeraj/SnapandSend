import unittest
from datetime import date, datetime, timezone

from src.rate_limiter import RateLimiter


class RateLimiterTests(unittest.TestCase):
    def setUp(self):
        self.limiter = RateLimiter(exemptUsernames={"unlimited-user"})

    def test_user_can_accept_photos_until_daily_limit(self):
        today = date(2026, 7, 28)

        for _ in range(30):
            self.assertTrue(self.limiter.canAcceptPhoto("user-1", today))
            self.limiter.recordPhoto("user-1", today)

        self.assertFalse(self.limiter.canAcceptPhoto("user-1", today))
        self.assertEqual(self.limiter.remainingPhotos("user-1", today), 0)

    def test_count_resets_on_a_new_day(self):
        firstDay = date(2026, 7, 28)
        nextDay = date(2026, 7, 29)

        for _ in range(30):
            self.limiter.recordPhoto("user-1", firstDay)

        self.assertTrue(self.limiter.canAcceptPhoto("user-1", nextDay))
        self.assertEqual(self.limiter.remainingPhotos("user-1", nextDay), 30)

    def test_exempt_user_has_no_limit(self):
        today = date(2026, 7, 28)
        userId = "user-1"
        userName = "unlimited-user"

        for _ in range(100):
            self.limiter.recordPhoto(userId, today, userName=userName)

        canAcceptPhoto = self.limiter.canAcceptPhoto(userId, today, userName)
        self.assertTrue(canAcceptPhoto)
        remainingPhotos = self.limiter.remainingPhotos(userId, today, userName)
        self.assertIsNone(remainingPhotos)

    def test_calendar_day_uses_singapore_timezone(self):
        receivedAt = datetime(2026, 7, 28, 16, 0, tzinfo=timezone.utc)

        calendarDay = self.limiter.getCalendarDay(receivedAt)
        self.assertEqual(calendarDay, date(2026, 7, 29))

    def test_default_exempt_username_has_no_limit(self):
        today = date(2026, 7, 28)
        limiter = RateLimiter()
        userId = "user-1"
        userName = "cr7neeraj"

        for _ in range(100):
            limiter.recordPhoto(userId, today, userName=userName)

        canAcceptPhoto = limiter.canAcceptPhoto(userId, today, userName)
        self.assertTrue(canAcceptPhoto)


if __name__ == "__main__":
    unittest.main()
