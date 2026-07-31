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
        self.effective_user.username = "user"


class FakeRouter:
    def handleStart(self, userId):
        return "start"

    def handleText(self, userId, text, receivedAt):
        return f"text: {text}"

    def handleImageUpload(self, userId):
        return "Image accepted. Send more or use /done when ready."


class FakePhotoBatchRouter:
    def acceptImage(self, userId, userName, imageBytes, receivedAt):
        return "Image accepted (1/15)."


class FakeDownloadedFile:
    async def download_as_bytearray(self):
        return bytearray(b"image")


class FakeTelegramFile:
    async def get_file(self):
        return FakeDownloadedFile()


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

    async def test_image_upload_replies_with_batch_acknowledgement(self):
        update = FakeUpdate()
        adapter = TelegramUpdateAdapter(FakeRouter(), FakePhotoBatchRouter())
        await adapter.handleImageUpload(update, "image/jpeg", 10, FakeTelegramFile())
        self.assertEqual(update.effective_message.replies, ["Image accepted (1/15)."])


if __name__ == "__main__":
    unittest.main()
