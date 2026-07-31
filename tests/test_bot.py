import unittest
from unittest.mock import patch

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


class BotTests(unittest.TestCase):
    def test_build_application_registers_start_done_and_text_handlers(self):
        settings = Settings(
            "token", "openai", "resend", "kms", "region", "users", "from", "model"
        )
        with patch("src.bot.buildRuntime") as runtime:
            runtime.return_value.telegramUpdateAdapter.handleStart = object()
            runtime.return_value.telegramUpdateAdapter.handleDone = object()
            runtime.return_value.telegramUpdateAdapter.handleText = object()
            with patch("src.bot.ApplicationBuilder", return_value=FakeBuilder()):
                application = buildApplication(settings)
        self.assertEqual(len(application.handlers), 5)
        self.assertIn("runtime", application.bot_data)
        self.assertIsNotNone(application.post_init)


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
