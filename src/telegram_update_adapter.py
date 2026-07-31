"""Telegram framework adapter for deterministic router responses."""

from datetime import datetime, timezone
from typing import Any

from src.image_intake import FileSizeLimitError, UnsupportedImageError
from src.image_intake import downloadImageBytes, validateImageUpload
from src.email_sender import EmailDeliveryError
from src.notes_curator import NotesCurationError
from src.telegram_router import EMAIL_SAVED_MESSAGE, IMAGE_ACCEPTED_MESSAGE
from src.vision_extractor import VisionExtractionError

PROCESSING_FAILURE_MESSAGE = "I could not process this batch. Please try again."


class TelegramUpdateAdapter:
    """Converts Telegram updates into router calls and replies."""

    def __init__(
        self,
        router: Any,
        photoBatchRouter: Any | None = None,
        doneBatchRouter: Any | None = None,
    ):
        self.router = router
        self.photoBatchRouter = photoBatchRouter
        self.doneBatchRouter = doneBatchRouter
        self.pendingUploads: dict[str, tuple[str | None, bytes, datetime]] = {}

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
        pendingUpload = self.pendingUploads.pop(userId, None)
        if response == EMAIL_SAVED_MESSAGE and pendingUpload:
            userName, imageBytes, uploadedAt = pendingUpload
            acknowledgement = self.photoBatchRouter.acceptImage(
                userId, userName, imageBytes, uploadedAt
            )
            await update.effective_message.reply_text(acknowledgement)

    async def handleImageUpload(
        self, update: Any, mimeType: str | None, fileSize: int, telegramFile: Any
    ) -> None:
        """Validate, download, and add one Telegram image to its batch."""

        try:
            validateImageUpload(mimeType, fileSize)
        except (UnsupportedImageError, FileSizeLimitError) as error:
            await update.effective_message.reply_text(str(error))
            return
        userId = str(update.effective_user.id)
        imageBytes = await downloadImageBytes(telegramFile)
        gateResponse = self.router.handleImageUpload(userId)
        if gateResponse != IMAGE_ACCEPTED_MESSAGE:
            self.pendingUploads[userId] = (
                update.effective_user.username,
                imageBytes,
                datetime.now(timezone.utc),
            )
            await update.effective_message.reply_text(gateResponse)
            return
        response = self.photoBatchRouter.acceptImage(
            userId,
            update.effective_user.username,
            imageBytes,
            datetime.now(timezone.utc),
        )
        await update.effective_message.reply_text(response)

    async def handleDone(self, update: Any) -> None:
        """Handle a Telegram /done update."""

        try:
            response = await self.doneBatchRouter.handleDone(
                str(update.effective_user.id)
            )
        except (EmailDeliveryError, NotesCurationError, VisionExtractionError):
            response = PROCESSING_FAILURE_MESSAGE
        await update.effective_message.reply_text(response)

    async def handleUnsupportedUpload(self, update: Any) -> None:
        """Handle a Telegram update carrying an unsupported content type."""

        await update.effective_message.reply_text(self.router.handleUnsupportedUpload())
