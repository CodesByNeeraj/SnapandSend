import unittest
from unittest.mock import AsyncMock, patch

from src.bot import buildApplication, notifyLostBatchesOnStartup
from src.config import Settings
from src.restart_notifier import REUPLOAD_AFTER_RESTART_MESSAGE


class FakeApplication:
    def __init__(self):
        self.handlers = []
        self.bot_data = {}
        self.post_init = None
        self.bot = None
        self.job_queue = type(
            "JobQueue", (), {"run_repeating": lambda *args, **kwargs: None}
        )()

    def add_handler(self, handler):
        self.handlers.append(handler)


class FakeBuilder:
    def token(self, token):
        return self

    def post_init(self, callback):
        self.postInitCallback = callback
        return self

    def build(self):
        application = FakeApplication()
        application.post_init = self.postInitCallback
        return application


class FakeUserStore:
    def __init__(self, pendingUserIds):
        self.pendingUserIds = pendingUserIds
        self.pendingClears = []

    def getUserIdsWithPendingBatch(self):
        return self.pendingUserIds

    def clearBatchPending(self, userId):
        self.pendingClears.append(userId)


class FakeBot:
    def __init__(self):
        self.sentMessages = []

    async def send_message(self, chat_id, text):
        self.sentMessages.append((chat_id, text))


def buildTestSettings() -> Settings:
    return Settings(
        "token",
        "openai",
        "resend",
        "kms",
        "region",
        "users",
        "from",
        "model",
        "langfuse-public",
        "langfuse-secret",
        "https://jp.cloud.langfuse.com",
    )


class FakeContext:
    def __init__(self, application):
        self.application = application


class BotTests(unittest.TestCase):
    def test_build_application_registers_start_done_and_text_handlers(self):
        with patch("src.bot.buildRuntime") as runtime:
            runtime.return_value.telegramUpdateAdapter.handleStart = object()
            runtime.return_value.telegramUpdateAdapter.handleDone = object()
            runtime.return_value.telegramUpdateAdapter.handleText = object()
            with patch("src.bot.ApplicationBuilder", return_value=FakeBuilder()):
                application = buildApplication(buildTestSettings())
        self.assertEqual(len(application.handlers), 7)
        self.assertIn("runtime", application.bot_data)
        self.assertIsNotNone(application.post_init)


class RegisteredHandlerCallbackTests(unittest.IsolatedAsyncioTestCase):
    """Invokes each registered handler the way python-telegram-bot actually
    does: callback(update, context) with both positional arguments. Earlier
    tests only asserted handler counts, so a callback signature mismatch
    (adapter methods only accepting `update`) went undetected until it
    broke every command against the real Telegram API."""

    async def test_start_done_and_text_handlers_dispatch_with_update_and_context(
        self,
    ):
        with patch("src.bot.buildRuntime") as runtime:
            adapter = runtime.return_value.telegramUpdateAdapter
            adapter.handleStart = AsyncMock()
            adapter.handleDone = AsyncMock()
            adapter.handleText = AsyncMock()
            with patch("src.bot.ApplicationBuilder", return_value=FakeBuilder()):
                application = buildApplication(buildTestSettings())

        update = object()
        context = FakeContext(application)
        startHandler, doneHandler, textHandler = application.handlers[:3]

        await startHandler.callback(update, context)
        await doneHandler.callback(update, context)
        await textHandler.callback(update, context)

        adapter.handleStart.assert_awaited_once_with(update)
        adapter.handleDone.assert_awaited_once_with(update)
        adapter.handleText.assert_awaited_once_with(update)

    async def test_csat_callback_handler_dispatches_with_update_and_context(self):
        with patch("src.bot.buildRuntime") as runtime:
            adapter = runtime.return_value.telegramUpdateAdapter
            adapter.handleCsatRating = AsyncMock()
            with patch("src.bot.ApplicationBuilder", return_value=FakeBuilder()):
                application = buildApplication(buildTestSettings())

        update = object()
        context = FakeContext(application)
        csatHandler = application.handlers[6]

        await csatHandler.callback(update, context)

        adapter.handleCsatRating.assert_awaited_once_with(update)


class NotifyLostBatchesOnStartupTests(unittest.IsolatedAsyncioTestCase):
    async def test_notifies_and_clears_users_with_a_pending_batch(self):
        application = FakeApplication()
        application.bot = FakeBot()
        userStore = FakeUserStore(["user-1"])
        application.bot_data["runtime"] = type(
            "Runtime", (), {"userStore": userStore}
        )()

        await notifyLostBatchesOnStartup(application)

        self.assertEqual(
            application.bot.sentMessages,
            [("user-1", REUPLOAD_AFTER_RESTART_MESSAGE)],
        )
        self.assertEqual(userStore.pendingClears, ["user-1"])


if __name__ == "__main__":
    unittest.main()
