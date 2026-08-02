"""Telegram framework adapter for deterministic router responses."""

import asyncio
from datetime import datetime, timezone
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from src.done_batch_router import (
    EMPTY_BATCH_MESSAGE,
    PROCESSING_STARTED_MESSAGE,
    NoBatchToProcessError,
)
from src.image_intake import FileSizeLimitError, UnsupportedImageError
from src.image_intake import downloadImageBytes, validateImageUpload
from src.email_sender import EmailDeliveryError
from src.notes_curator import NotesCurationError
from src.satisfaction_survey import (
    CSAT_CALLBACK_PREFIX,
    SURVEY_MESSAGE,
    THANK_YOU_MESSAGE,
    shouldPromptForSatisfaction,
)
from src.telegram_router import EMAIL_SAVED_MESSAGE, IMAGE_ACCEPTED_MESSAGE
from src.vision_extractor import VisionExtractionError

PROCESSING_FAILURE_MESSAGE = "I could not process this batch. Please try again."


def buildSurveyKeyboard() -> InlineKeyboardMarkup:
    """Build a two-row 1-10 CSAT rating keyboard."""

    def ratingButton(score: int) -> InlineKeyboardButton:
        return InlineKeyboardButton(
            str(score), callback_data=f"{CSAT_CALLBACK_PREFIX}{score}"
        )

    return InlineKeyboardMarkup(
        [
            [ratingButton(score) for score in range(1, 6)],
            [ratingButton(score) for score in range(6, 11)],
        ]
    )


class TelegramUpdateAdapter:
    """Converts Telegram updates into router calls and replies."""

    def __init__(
        self,
        router: Any,
        photoBatchRouter: Any | None = None,
        doneBatchRouter: Any | None = None,
        userStore: Any | None = None,
    ):
        self.router = router
        self.photoBatchRouter = photoBatchRouter
        self.doneBatchRouter = doneBatchRouter
        self.userStore = userStore
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

    async def handleDone(self, update: Any) -> "asyncio.Task[None] | None":
        """Handle a Telegram /done update.

        Replies immediately, then runs extraction, curation, and delivery in
        the background so a slow batch does not delay replies to other
        users' updates. Returns the background task so tests can await it;
        production callers do not need the return value.
        """

        userId = str(update.effective_user.id)
        try:
            recipientEmail, images = self.doneBatchRouter.closeBatchForProcessing(
                userId
            )
        except NoBatchToProcessError:
            await update.effective_message.reply_text(EMPTY_BATCH_MESSAGE)
            return None

        await update.effective_message.reply_text(PROCESSING_STARTED_MESSAGE)
        return asyncio.create_task(
            self._completeProcessingAndNotify(update, userId, recipientEmail, images)
        )

    async def _completeProcessingAndNotify(
        self, update: Any, userId: str, recipientEmail: str, images: list[bytes]
    ) -> None:
        """Finish processing a closed batch and report the outcome."""

        response, usageCount = await self._resolveProcessingOutcome(
            userId, recipientEmail, images
        )
        await update.effective_message.reply_text(response)
        if usageCount is not None and shouldPromptForSatisfaction(usageCount):
            await update.effective_message.reply_text(
                SURVEY_MESSAGE, reply_markup=buildSurveyKeyboard()
            )

    async def notifyExpiredBatchProcessing(
        self, bot: Any, userId: str, recipientEmail: str, images: list[bytes]
    ) -> None:
        """Notify a user their timed-out batch is processing, then report
        the outcome, mirroring the two-message /done flow for a batch the
        user never explicitly closed themselves."""

        await bot.send_message(chat_id=userId, text=PROCESSING_STARTED_MESSAGE)
        response, usageCount = await self._resolveProcessingOutcome(
            userId, recipientEmail, images
        )
        await bot.send_message(chat_id=userId, text=response)
        if usageCount is not None and shouldPromptForSatisfaction(usageCount):
            await bot.send_message(
                chat_id=userId, text=SURVEY_MESSAGE, reply_markup=buildSurveyKeyboard()
            )

    async def _resolveProcessingOutcome(
        self, userId: str, recipientEmail: str, images: list[bytes]
    ) -> tuple[str, int | None]:
        try:
            return await self.doneBatchRouter.completeProcessing(
                recipientEmail, images, userId
            )
        except (EmailDeliveryError, NotesCurationError, VisionExtractionError):
            return PROCESSING_FAILURE_MESSAGE, None

    async def handleCsatRating(self, update: Any) -> None:
        """Record a tapped CSAT rating and replace the buttons with thanks."""

        query = update.callback_query
        userId = str(query.from_user.id)
        score = int(query.data.removeprefix(CSAT_CALLBACK_PREFIX))
        self.userStore.recordCsatScore(userId, score, datetime.now(timezone.utc))
        await query.answer()
        await query.edit_message_text(THANK_YOU_MESSAGE)

    async def handleUnsupportedUpload(self, update: Any) -> None:
        """Handle a Telegram update carrying an unsupported content type."""

        await update.effective_message.reply_text(self.router.handleUnsupportedUpload())

    async def handleUnknownCommand(self, update: Any) -> None:
        """Handle a Telegram update carrying an unrecognized command."""

        await update.effective_message.reply_text(self.router.handleUnknownCommand())
