"""Deterministic /done closure and batch processing."""

from typing import Any

from src.batch_manager import EmptyBatchError

EMPTY_BATCH_MESSAGE = "Please upload at least one photo before using /done."
PROCESSING_STARTED_MESSAGE = (
    "I will update you when your images have been processed and the email "
    "has been sent!"
)
EMAIL_SENT_MESSAGE = "Email sent! Check your inbox for your notes."
UNREADABLE_BATCH_MESSAGE = (
    "I could not find readable text in the images. Please upload clearer photos."
)


class NoBatchToProcessError(ValueError):
    """Raised when a user has no closable batch or no registered email."""


class DoneBatchRouter:
    """Closes a batch and submits it to the BatchOrchestrator."""

    def __init__(self, batchManager: Any, userStore: Any, batchOrchestrator: Any):
        self.batchManager = batchManager
        self.userStore = userStore
        self.batchOrchestrator = batchOrchestrator

    def closeBatchForProcessing(self, userId: str) -> tuple[str, list[bytes]]:
        """Close a user's batch and resolve their recipient email.

        Raises NoBatchToProcessError if there is nothing to process, so the
        caller can reply immediately without waiting on the slow part below.
        """

        try:
            images = self.batchManager.closeBatch(userId)
        except EmptyBatchError:
            raise NoBatchToProcessError() from None
        self.userStore.clearBatchPending(userId)
        recipientEmail = self.userStore.getEmail(userId)
        if not recipientEmail:
            raise NoBatchToProcessError()
        return recipientEmail, images

    async def completeProcessing(
        self, recipientEmail: str, images: list[bytes], userId: str
    ) -> tuple[str, int | None]:
        """Run extraction, curation, and delivery.

        Returns the outcome message, plus the user's updated completed-batch
        usage count on success or None on an unreadable batch (nothing was
        actually delivered, so it should not count as a use).
        """

        emailId = await self.batchOrchestrator.processBatch(recipientEmail, images)
        if emailId is None:
            return UNREADABLE_BATCH_MESSAGE, None
        usageCount = self.userStore.incrementUsageCount(userId)
        return EMAIL_SENT_MESSAGE, usageCount
