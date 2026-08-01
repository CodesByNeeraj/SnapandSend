import unittest

from src.done_batch_router import NoBatchToProcessError
from src.satisfaction_survey import SURVEY_MESSAGE
from src.telegram_update_adapter import TelegramUpdateAdapter
from src.vision_extractor import VisionExtractionError


class FakeMessage:
    def __init__(self, text="hello"):
        self.text = text
        self.replies = []
        self.replyMarkups = []

    async def reply_text(self, text, reply_markup=None):
        self.replies.append(text)
        self.replyMarkups.append(reply_markup)


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

    def handleUnsupportedUpload(self):
        return "Only image files are supported."


class AwaitingEmailRouter(FakeRouter):
    def handleImageUpload(self, userId):
        return "Reply with your email address before sending photos."

    def handleText(self, userId, text, receivedAt):
        return "Your email has been saved. You can now send photos."


class FakePhotoBatchRouter:
    def acceptImage(self, userId, userName, imageBytes, receivedAt):
        return "Image accepted (1/15)."


class FakeDoneBatchRouter:
    def __init__(self, usageCount=1):
        self.usageCount = usageCount

    def closeBatchForProcessing(self, userId):
        return "person@example.com", [b"image"]

    async def completeProcessing(self, recipientEmail, images, userId):
        return "Email sent! Check your inbox for your notes.", self.usageCount


class EmptyBatchDoneBatchRouter:
    def closeBatchForProcessing(self, userId):
        raise NoBatchToProcessError()


class FailingDoneBatchRouter(FakeDoneBatchRouter):
    async def completeProcessing(self, recipientEmail, images, userId):
        raise VisionExtractionError("failed")


class FakeBot:
    def __init__(self):
        self.sentMessages = []
        self.sentMarkups = []

    async def send_message(self, chat_id, text, reply_markup=None):
        self.sentMessages.append((chat_id, text))
        self.sentMarkups.append(reply_markup)


class FakeUserStore:
    def __init__(self):
        self.recorded = []

    def recordCsatScore(self, userId, score, ratedAt):
        self.recorded.append((userId, score))


class FakeCallbackQuery:
    def __init__(self, data, userId):
        self.data = data
        self.from_user = type("User", (), {"id": userId})()
        self.answered = False
        self.editedTexts = []

    async def answer(self):
        self.answered = True

    async def edit_message_text(self, text):
        self.editedTexts.append(text)


class FakeCallbackUpdate:
    def __init__(self, data, userId):
        self.callback_query = FakeCallbackQuery(data, userId)


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

    async def test_email_reply_continues_pending_image_upload(self):
        adapter = TelegramUpdateAdapter(AwaitingEmailRouter(), FakePhotoBatchRouter())
        uploadUpdate = FakeUpdate()
        await adapter.handleImageUpload(
            uploadUpdate, "image/jpeg", 10, FakeTelegramFile()
        )
        emailUpdate = FakeUpdate("person@example.com")

        await adapter.handleText(emailUpdate)

        self.assertEqual(
            emailUpdate.effective_message.replies,
            [
                "Your email has been saved. You can now send photos.",
                "Image accepted (1/15).",
            ],
        )

    async def test_done_immediately_acknowledges_then_reports_email_sent(self):
        update = FakeUpdate()
        adapter = TelegramUpdateAdapter(
            FakeRouter(), doneBatchRouter=FakeDoneBatchRouter()
        )
        backgroundTask = await adapter.handleDone(update)
        self.assertEqual(
            update.effective_message.replies,
            [
                "I will update you when your images have been processed and the "
                "email has been sent!"
            ],
        )

        await backgroundTask

        self.assertEqual(
            update.effective_message.replies,
            [
                "I will update you when your images have been processed and the "
                "email has been sent!",
                "Email sent! Check your inbox for your notes.",
            ],
        )

    async def test_done_with_no_batch_replies_with_empty_batch_message_only(self):
        update = FakeUpdate()
        adapter = TelegramUpdateAdapter(
            FakeRouter(), doneBatchRouter=EmptyBatchDoneBatchRouter()
        )
        backgroundTask = await adapter.handleDone(update)
        self.assertIsNone(backgroundTask)
        self.assertEqual(
            update.effective_message.replies,
            ["Please upload at least one photo before using /done."],
        )

    async def test_done_reports_processing_failure_after_acknowledging(self):
        update = FakeUpdate()
        adapter = TelegramUpdateAdapter(
            FakeRouter(), doneBatchRouter=FailingDoneBatchRouter()
        )
        backgroundTask = await adapter.handleDone(update)

        await backgroundTask

        self.assertIn("could not process", update.effective_message.replies[1])

    async def test_done_prompts_satisfaction_survey_at_threshold_usage_count(self):
        update = FakeUpdate()
        adapter = TelegramUpdateAdapter(
            FakeRouter(), doneBatchRouter=FakeDoneBatchRouter(usageCount=3)
        )
        backgroundTask = await adapter.handleDone(update)

        await backgroundTask

        self.assertEqual(len(update.effective_message.replies), 3)
        self.assertEqual(update.effective_message.replies[2], SURVEY_MESSAGE)
        self.assertIsNotNone(update.effective_message.replyMarkups[2])

    async def test_done_does_not_prompt_survey_below_threshold_usage_count(self):
        update = FakeUpdate()
        adapter = TelegramUpdateAdapter(
            FakeRouter(), doneBatchRouter=FakeDoneBatchRouter(usageCount=1)
        )
        backgroundTask = await adapter.handleDone(update)

        await backgroundTask

        self.assertEqual(len(update.effective_message.replies), 2)

    async def test_notify_expired_batch_acknowledges_then_reports_email_sent(self):
        bot = FakeBot()
        adapter = TelegramUpdateAdapter(
            FakeRouter(), doneBatchRouter=FakeDoneBatchRouter()
        )

        await adapter.notifyExpiredBatchProcessing(
            bot, "user-1", "person@example.com", [b"image"]
        )

        self.assertEqual(
            bot.sentMessages,
            [
                (
                    "user-1",
                    "I will update you when your images have been processed and "
                    "the email has been sent!",
                ),
                ("user-1", "Email sent! Check your inbox for your notes."),
            ],
        )

    async def test_notify_expired_batch_reports_processing_failure(self):
        bot = FakeBot()
        adapter = TelegramUpdateAdapter(
            FakeRouter(), doneBatchRouter=FailingDoneBatchRouter()
        )

        await adapter.notifyExpiredBatchProcessing(
            bot, "user-1", "person@example.com", [b"image"]
        )

        self.assertIn("could not process", bot.sentMessages[1][1])

    async def test_notify_expired_batch_prompts_survey_at_threshold_usage_count(self):
        bot = FakeBot()
        adapter = TelegramUpdateAdapter(
            FakeRouter(), doneBatchRouter=FakeDoneBatchRouter(usageCount=30)
        )

        await adapter.notifyExpiredBatchProcessing(
            bot, "user-1", "person@example.com", [b"image"]
        )

        self.assertEqual(len(bot.sentMessages), 3)
        self.assertEqual(bot.sentMessages[2], ("user-1", SURVEY_MESSAGE))
        self.assertIsNotNone(bot.sentMarkups[2])

    async def test_handle_csat_rating_records_score_and_thanks_user(self):
        userStore = FakeUserStore()
        adapter = TelegramUpdateAdapter(FakeRouter(), userStore=userStore)
        update = FakeCallbackUpdate("csat:7", 42)

        await adapter.handleCsatRating(update)

        self.assertEqual(userStore.recorded, [("42", 7)])
        self.assertTrue(update.callback_query.answered)
        self.assertEqual(update.callback_query.editedTexts, ["Thank you!"])

    async def test_unsupported_upload_replies_with_router_response(self):
        update = FakeUpdate()
        adapter = TelegramUpdateAdapter(FakeRouter())
        await adapter.handleUnsupportedUpload(update)
        self.assertEqual(
            update.effective_message.replies, ["Only image files are supported."]
        )


if __name__ == "__main__":
    unittest.main()
