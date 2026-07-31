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
    application.bot_data["runtime"] = runtime
    return application


def runBot() -> None:
    """Load settings and start Telegram long polling."""

    application = buildApplication(Settings.fromEnvironment())
    application.run_polling()
