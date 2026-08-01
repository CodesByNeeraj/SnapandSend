"""Periodic trigger for expired photo batch processing."""

from datetime import datetime, timezone
from typing import Any


class TimeoutScheduler:
    """Runs one expired-batch closure cycle."""

    def __init__(self, expiredBatchProcessor: Any):
        self.expiredBatchProcessor = expiredBatchProcessor

    def getExpiredBatchesForProcessing(self) -> list[tuple[str, str, list[bytes]]]:
        """Close batches inactive for the configured timeout window."""

        return self.expiredBatchProcessor.closeExpiredBatchesForProcessing(
            datetime.now(timezone.utc)
        )
