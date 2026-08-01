"""Deterministic Telegram message routing state."""

import re
from datetime import datetime
from typing import Any

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
START_MESSAGE = (
    "Send photos that contain slides, whiteboards, or documents and I will email your "
    "notes. Images are sent to OpenAI for extraction and notes are delivered "
    "through Resend. Reply with your email address to begin."
)
INVALID_EMAIL_MESSAGE = "Please reply with a valid email address."
EMAIL_SAVED_MESSAGE = "Your email has been saved. You can now send photos."
HELP_MESSAGE = (
    "Send an image or images that you want me to extract text from and I "
    "will format them nicely and drop it in your inbox!"
)
EMAIL_REQUIRED_MESSAGE = "Reply with your email address before sending photos."
RETURNING_USER_START_MESSAGE = "Upload an image to get started."
IMAGE_ACCEPTED_MESSAGE = "Image accepted. Send more or use /done when ready."
UNSUPPORTED_UPLOAD_MESSAGE = "Only image files are supported."


class TelegramRouter:
    """Routes onboarding text without model inference."""

    def __init__(self, userStore: Any):
        self.userStore = userStore
        self.awaitingEmail: dict[str, bool] = {}

    def handleStart(self, userId: str) -> str:
        """Begin email registration for a new user, or prompt a returning one.

        A returning user (one with a registered email) is not put back into
        the awaiting-email state, since their next plain-text message would
        otherwise be silently treated as an email reply and, if it happened
        to look like one, overwrite their real registered address.
        """

        if self.userStore.getEmail(userId):
            return RETURNING_USER_START_MESSAGE
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

    def handleImageUpload(self, userId: str) -> str:
        """Require a registered email before accepting an image upload."""

        if self.userStore.getEmail(userId):
            return IMAGE_ACCEPTED_MESSAGE
        self.awaitingEmail[userId] = True
        return EMAIL_REQUIRED_MESSAGE

    def handleUnsupportedUpload(self) -> str:
        """Return the fixed response for non-image uploads."""

        return UNSUPPORTED_UPLOAD_MESSAGE
