"""Periodic trigger for expired photo batch processing."""

from datetime import datetime, timezone
from typing import Any


class TimeoutScheduler:
    """Runs one expired-batch processing cycle."""

    def __init__(self, expiredBatchProcessor: Any):
        self.expiredBatchProcessor = expiredBatchProcessor

    async def processExpiredBatches(self) -> int:
        """Process batches inactive for the configured timeout window."""

        return await self.expiredBatchProcessor.processExpiredBatches(
            datetime.now(timezone.utc)
        )
