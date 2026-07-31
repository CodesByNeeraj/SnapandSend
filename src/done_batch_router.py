"""Deterministic /done closure and batch processing."""

from typing import Any

from src.batch_manager import EmptyBatchError

EMPTY_BATCH_MESSAGE = "Please upload at least one photo before using /done."
PROCESSING_MESSAGE = "Your notes are being prepared."


class DoneBatchRouter:
    """Closes a batch and submits it to the BatchOrchestrator."""

    def __init__(self, batchManager: Any, userStore: Any, batchOrchestrator: Any):
        self.batchManager = batchManager
        self.userStore = userStore
        self.batchOrchestrator = batchOrchestrator

    async def handleDone(self, userId: str) -> str:
        """Close the batch and process it with the registered recipient email."""

        try:
            images = self.batchManager.closeBatch(userId)
        except EmptyBatchError:
            return EMPTY_BATCH_MESSAGE
        recipientEmail = self.userStore.getEmail(userId)
        if not recipientEmail:
            return EMPTY_BATCH_MESSAGE
        await self.batchOrchestrator.processBatch(recipientEmail, images)
        return PROCESSING_MESSAGE
