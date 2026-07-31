import unittest
from unittest.mock import patch

from src.bot import buildApplication
from src.config import Settings


class FakeApplication:
    def __init__(self):
        self.handlers = []
        self.bot_data = {}

    def add_handler(self, handler):
        self.handlers.append(handler)


class FakeBuilder:
    def token(self, token):
        return self

    def build(self):
        return FakeApplication()


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


if __name__ == "__main__":
    unittest.main()
