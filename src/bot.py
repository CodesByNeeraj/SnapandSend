"""Telegram long-polling entrypoint for Snap&Send."""

from dotenv import load_dotenv

# Loaded before src.runtime so LANGFUSE_* env vars are already set by the
# time that module imports langfuse.openai, per Langfuse's own guidance on
# import order.
load_dotenv()

from telegram.ext import (  # noqa: E402
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)

from src.config import Settings  # noqa: E402
from src.restart_notifier import RestartNotifier  # noqa: E402
from src.runtime import buildRuntime  # noqa: E402

TIMEOUT_CHECK_SECONDS = 30


def buildApplication(settings: Settings) -> Application:
    """Build a configured Telegram application without starting polling."""

    runtime = buildRuntime(settings)
    application = (
        ApplicationBuilder()
        .token(settings.telegramBotToken)
        .post_init(notifyLostBatchesOnStartup)
        .build()
    )
    application.add_handler(CommandHandler("start", handleStartCommand))
    application.add_handler(CommandHandler("done", handleDoneCommand))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handleTextMessage)
    )
    application.add_handler(MessageHandler(filters.PHOTO, handlePhotoUpload))
    application.add_handler(MessageHandler(filters.Document.ALL, handleDocumentUpload))
    application.add_handler(MessageHandler(filters.ALL, handleUnsupportedMessage))
    application.bot_data["runtime"] = runtime
    application.job_queue.run_repeating(
        processExpiredBatches,
        interval=TIMEOUT_CHECK_SECONDS,
        name="expired-batch-processor",
    )
    return application


async def handleStartCommand(update: object, context: object) -> None:
    """Adapt a Telegram /start update to the shared start handler."""

    adapter = context.application.bot_data["runtime"].telegramUpdateAdapter
    await adapter.handleStart(update)


async def handleDoneCommand(update: object, context: object) -> None:
    """Adapt a Telegram /done update to the shared done handler."""

    adapter = context.application.bot_data["runtime"].telegramUpdateAdapter
    await adapter.handleDone(update)


async def handleTextMessage(update: object, context: object) -> None:
    """Adapt a Telegram text update to the shared text handler."""

    adapter = context.application.bot_data["runtime"].telegramUpdateAdapter
    await adapter.handleText(update)


async def notifyLostBatchesOnStartup(application: object) -> None:
    """Warn any user left with an unrecoverable batch by a crash or restart."""

    runtime = application.bot_data["runtime"]
    await RestartNotifier(application.bot, runtime.userStore).notifyLostBatches()


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


async def handleUnsupportedMessage(update: object, context: object) -> None:
    """Adapt any other Telegram update to the fixed unsupported-upload reply."""

    adapter = context.application.bot_data["runtime"].telegramUpdateAdapter
    await adapter.handleUnsupportedUpload(update)


def runBot() -> None:
    """Load settings and start Telegram long polling."""

    application = buildApplication(Settings.fromEnvironment())
    application.run_polling()


if __name__ == "__main__":
    runBot()
