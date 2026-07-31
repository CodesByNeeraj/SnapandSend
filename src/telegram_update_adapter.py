"""Telegram framework adapter for deterministic router responses."""

from datetime import datetime, timezone
from typing import Any


class TelegramUpdateAdapter:
    """Converts Telegram updates into router calls and replies."""

    def __init__(self, router: Any):
        self.router = router

    async def handleStart(self, update: Any) -> None:
        """Handle a Telegram /start update."""

        userId = str(update.effective_user.id)
        await update.effective_message.reply_text(self.router.handleStart(userId))

    async def handleText(self, update: Any) -> None:
        """Handle a plain-text Telegram update."""

        userId = str(update.effective_user.id)
        receivedAt = datetime.now(timezone.utc)
        response = self.router.handleText(
            userId, update.effective_message.text, receivedAt
        )
        await update.effective_message.reply_text(response)
