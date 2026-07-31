"""Deterministic Telegram message routing state."""

import re
from datetime import datetime
from typing import Any

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
START_MESSAGE = (
    "Send photos of slides, whiteboards, or documents and I will email your "
    "notes. Images are sent to OpenAI for extraction and notes are delivered "
    "through Resend. Reply with your email address to begin."
)
INVALID_EMAIL_MESSAGE = "Please reply with a valid email address."
EMAIL_SAVED_MESSAGE = "Your email has been saved. You can now send photos."
HELP_MESSAGE = "Send a photo or document image to start a notes batch."


class TelegramRouter:
    """Routes onboarding text without model inference."""

    def __init__(self, userStore: Any):
        self.userStore = userStore
        self.awaitingEmail: dict[str, bool] = {}

    def handleStart(self, userId: str) -> str:
        """Begin email registration and disclose data handling."""

        self.awaitingEmail[userId] = True
        return START_MESSAGE

    def handleText(self, userId: str, text: str, receivedAt: datetime) -> str:
        """Save a requested email address or return fixed help text."""

        if not self.awaitingEmail.get(userId):
            return HELP_MESSAGE
        email = text.strip()
        if not EMAIL_PATTERN.fullmatch(email):
            return INVALID_EMAIL_MESSAGE
        self.userStore.saveEmail(userId, email, receivedAt)
        self.awaitingEmail.pop(userId)
        return EMAIL_SAVED_MESSAGE
