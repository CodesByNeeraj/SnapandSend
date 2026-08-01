"""Timeout-driven closure of expired photo batches."""

from datetime import datetime
from typing import Any


class ExpiredBatchProcessor:
    """Closes expired batches and resolves each one's recipient email."""

    def __init__(self, batchManager: Any, userStore: Any):
        self.batchManager = batchManager
        self.userStore = userStore

    def closeExpiredBatchesForProcessing(
        self, currentTime: datetime
    ) -> list[tuple[str, str, list[bytes]]]:
        """Close every expired batch, returning ones with a registered email.

        Each entry is (userId, recipientEmail, images), ready for the
        caller to process and notify. Users without a registered email are
        skipped, since there is nowhere to deliver their notes.
        """

        expiredBatches = self.batchManager.closeExpiredBatches(currentTime)
        ready = []
        for userId, images in expiredBatches.items():
            self.userStore.clearBatchPending(userId)
            recipientEmail = self.userStore.getEmail(userId)
            if recipientEmail:
                ready.append((userId, recipientEmail, images))
        return ready
