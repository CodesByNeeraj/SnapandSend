"""Telegram long-polling entrypoint for Snap&Send."""

from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)

from src.config import Settings
from src.runtime import buildRuntime

TIMEOUT_CHECK_SECONDS = 30


def buildApplication(settings: Settings) -> Application:
    """Build a configured Telegram application without starting polling."""

    runtime = buildRuntime(settings)
    application = ApplicationBuilder().token(settings.telegramBotToken).build()
    adapter = runtime.telegramUpdateAdapter
    application.add_handler(CommandHandler("start", adapter.handleStart))
    application.add_handler(CommandHandler("done", adapter.handleDone))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, adapter.handleText)
    )
    application.add_handler(MessageHandler(filters.PHOTO, handlePhotoUpload))
    application.add_handler(MessageHandler(filters.Document.ALL, handleDocumentUpload))
    application.bot_data["runtime"] = runtime
    application.job_queue.run_repeating(
        processExpiredBatches,
        interval=TIMEOUT_CHECK_SECONDS,
        name="expired-batch-processor",
    )
    return application


async def processExpiredBatches(context: object) -> None:
    """Run one periodic expired-batch processing cycle."""

    await context.application.bot_data[
        "runtime"
    ].timeoutScheduler.processExpiredBatches()


async def handlePhotoUpload(update: object, context: object) -> None:
    """Adapt a Telegram photo update to the shared image handler."""

    adapter = context.application.bot_data["runtime"].telegramUpdateAdapter
    photo = update.effective_message.photo[-1]
    await adapter.handleImageUpload(update, "image/jpeg", photo.file_size or 0, photo)


async def handleDocumentUpload(update: object, context: object) -> None:
    """Adapt a Telegram document update to the shared image handler."""

    adapter = context.application.bot_data["runtime"].telegramUpdateAdapter
    document = update.effective_message.document
    await adapter.handleImageUpload(
        update, document.mime_type, document.file_size or 0, document
    )


def runBot() -> None:
    """Load settings and start Telegram long polling."""

    application = buildApplication(Settings.fromEnvironment())
    application.run_polling()
