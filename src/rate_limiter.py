"""In-memory per-user daily photo rate limiting."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from src.constants import (
    DAILY_PHOTO_LIMIT,
    DEFAULT_EXEMPT_USERNAMES,
    RATE_LIMIT_TIMEZONE,
)


class RateLimiter:
    """Tracks accepted photo counts for the current bot process."""

    def __init__(self, exemptUsernames: set[str] | None = None):
        self.exemptUsernames = exemptUsernames or set(DEFAULT_EXEMPT_USERNAMES)
        self.photoCounts: dict[tuple[str, date], int] = {}

    def getCalendarDay(self, receivedAt: datetime) -> date:
        """Return the Singapore calendar day for an accepted photo."""

        return receivedAt.astimezone(ZoneInfo(RATE_LIMIT_TIMEZONE)).date()

    def canAcceptPhoto(
        self,
        userId: str,
        calendarDay: date,
        userName: str | None = None,
    ) -> bool:
        """Return whether the user may submit another photo today."""

        if userName in self.exemptUsernames:
            return True
        acceptedPhotos = self.photoCounts.get((userId, calendarDay), 0)
        return acceptedPhotos < DAILY_PHOTO_LIMIT

    def recordPhoto(
        self,
        userId: str,
        calendarDay: date,
        userName: str | None = None,
    ) -> None:
        """Record one accepted photo for the user and calendar day."""

        if userName in self.exemptUsernames:
            return
        key = (userId, calendarDay)
        self.photoCounts[key] = self.photoCounts.get(key, 0) + 1

    def remainingPhotos(
        self,
        userId: str,
        calendarDay: date,
        userName: str | None = None,
    ) -> int | None:
        """Return remaining capacity, or ``None`` for an exempt user."""

        if userName in self.exemptUsernames:
            return None
        count = self.photoCounts.get((userId, calendarDay), 0)
        return max(DAILY_PHOTO_LIMIT - count, 0)
