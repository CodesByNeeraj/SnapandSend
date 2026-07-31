import unittest

from src.telegram_update_adapter import TelegramUpdateAdapter


class FakeMessage:
    def __init__(self, text="hello"):
        self.text = text
        self.replies = []

    async def reply_text(self, text):
        self.replies.append(text)


class FakeUpdate:
    def __init__(self, text="hello"):
        self.effective_user = type("User", (), {"id": 12})()
        self.effective_message = FakeMessage(text)


class FakeRouter:
    def handleStart(self, userId):
        return "start"

    def handleText(self, userId, text, receivedAt):
        return f"text: {text}"


class TelegramUpdateAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_start_replies_with_router_response(self):
        update = FakeUpdate()
        adapter = TelegramUpdateAdapter(FakeRouter())
        await adapter.handleStart(update)
        self.assertEqual(update.effective_message.replies, ["start"])

    async def test_text_replies_with_router_response(self):
        update = FakeUpdate("person@example.com")
        adapter = TelegramUpdateAdapter(FakeRouter())
        await adapter.handleText(update)
        self.assertEqual(update.effective_message.replies, ["text: person@example.com"])


if __name__ == "__main__":
    unittest.main()
