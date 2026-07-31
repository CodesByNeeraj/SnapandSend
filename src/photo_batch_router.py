"""Deterministic acceptance of prepared image uploads into photo batches."""

from datetime import datetime
from typing import Any

RATE_LIMIT_MESSAGE = "You have reached today's photo limit."
BATCH_LIMIT_MESSAGE = "This batch already has 15 photos. Use /done to send it."


class PhotoBatchRouter:
    """Composes rate limiting, image preparation, and batch storage."""

    def __init__(
        self, rateLimiter: Any, batchManager: Any, imagePreparer: Any, userStore: Any
    ):
        self.rateLimiter = rateLimiter
        self.batchManager = batchManager
        self.imagePreparer = imagePreparer
        self.userStore = userStore

    def acceptImage(
        self,
        userId: str,
        userName: str | None,
        imageBytes: bytes,
        receivedAt: datetime,
    ) -> str:
        """Add one valid image and return its immediate acknowledgement."""

        calendarDay = self.rateLimiter.getCalendarDay(receivedAt)
        if not self.rateLimiter.canAcceptPhoto(userId, calendarDay, userName):
            return RATE_LIMIT_MESSAGE
        preparedImage = self.imagePreparer(imageBytes)
        try:
            count = self.batchManager.addPhoto(userId, preparedImage, receivedAt)
        except ValueError:
            return BATCH_LIMIT_MESSAGE
        if count == 1:
            self.userStore.markBatchPending(userId)
        self.rateLimiter.recordPhoto(userId, calendarDay, userName)
        return f"Image accepted ({count}/15). Send more or use /done within 3 minutes."
