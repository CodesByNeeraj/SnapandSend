"""In-memory ordered photo batches and inactivity expiry checks."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from src.constants import BATCH_INACTIVITY_SECONDS, MAX_BATCH_PHOTOS


class EmptyBatchError(ValueError):
    """Raised when a caller tries to close a missing or empty batch."""


class BatchLimitError(ValueError):
    """Raised when a batch already contains the maximum number of photos."""


MAX_BATCH_ERROR_MESSAGE = "This batch already contains the maximum photos"


@dataclass
class PhotoBatch:
    photos: list[bytes] = field(default_factory=list)
    lastPhotoAt: datetime | None = None


class BatchManager:
    """Stores current user batches in process memory."""

    def __init__(self):
        self.batches: dict[str, PhotoBatch] = {}

    def addPhoto(
        self,
        userId: str,
        imageBytes: bytes,
        receivedAt: datetime,
    ) -> int:
        """Append a photo and return the user's new batch count."""

        batch = self.batches.setdefault(userId, PhotoBatch())
        if len(batch.photos) >= MAX_BATCH_PHOTOS:
            raise BatchLimitError(MAX_BATCH_ERROR_MESSAGE)
        batch.photos.append(imageBytes)
        batch.lastPhotoAt = receivedAt
        return len(batch.photos)

    def getPhotos(self, userId: str) -> list[bytes]:
        """Return a copy of the current ordered photos for a user."""

        batch = self.batches.get(userId)
        return list(batch.photos) if batch else []

    def closeBatch(self, userId: str) -> list[bytes]:
        """Remove and return a user's current photos."""

        batch = self.batches.pop(userId, None)
        if not batch or not batch.photos:
            raise EmptyBatchError("There is no photo batch for this user")
        return list(batch.photos)

    def getExpiredUserIds(self, currentTime: datetime) -> list[str]:
        """Return users whose latest photo is at least three minutes old."""

        timeout = timedelta(seconds=BATCH_INACTIVITY_SECONDS)
        return [
            userId
            for userId, batch in self.batches.items()
            if batch.lastPhotoAt is not None
            and currentTime - batch.lastPhotoAt >= timeout
        ]
