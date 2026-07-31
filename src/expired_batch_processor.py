"""Timeout-driven processing of closed photo batches."""

from datetime import datetime
from typing import Any


class ExpiredBatchProcessor:
    """Submits atomically closed expired batches to the orchestrator."""

    def __init__(self, batchManager: Any, userStore: Any, batchOrchestrator: Any):
        self.batchManager = batchManager
        self.userStore = userStore
        self.batchOrchestrator = batchOrchestrator

    async def processExpiredBatches(self, currentTime: datetime) -> int:
        """Process all expired batches and return their count."""

        expiredBatches = self.batchManager.closeExpiredBatches(currentTime)
        for userId, images in expiredBatches.items():
            self.userStore.clearBatchPending(userId)
            recipientEmail = self.userStore.getEmail(userId)
            if recipientEmail:
                await self.batchOrchestrator.processBatch(recipientEmail, images)
        return len(expiredBatches)
