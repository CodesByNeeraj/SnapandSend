import unittest
from datetime import datetime, timezone

from src.telegram_router import TelegramRouter


class FakeUserStore:
    def __init__(self):
        self.saved = []

    def saveEmail(self, userId, email, createdAt):
        self.saved.append((userId, email, createdAt))

    def getEmail(self, userId):
        return "person@example.com" if userId == "registered" else None


class TelegramRouterTests(unittest.TestCase):
    def test_start_prompts_for_email_and_discloses_data_handling(self):
        router = TelegramRouter(FakeUserStore())

        response = router.handleStart("user-1")

        self.assertIn("email", response.lower())
        self.assertIn("OpenAI", response)
        self.assertTrue(router.awaitingEmail["user-1"])

    def test_start_for_registered_user_prompts_to_upload_without_resetting_state(self):
        router = TelegramRouter(FakeUserStore())

        response = router.handleStart("registered")

        self.assertEqual(response, "Upload an image to get started.")
        self.assertNotIn("registered", router.awaitingEmail)

    def test_email_reply_saves_registered_address_and_clears_waiting_state(self):
        store = FakeUserStore()
        router = TelegramRouter(store)
        router.handleStart("user-1")
        now = datetime(2026, 7, 31, tzinfo=timezone.utc)

        response = router.handleText("user-1", "person@example.com", now)

        self.assertIn("saved", response.lower())
        self.assertEqual(store.saved, [("user-1", "person@example.com", now)])
        self.assertNotIn("user-1", router.awaitingEmail)

    def test_invalid_email_keeps_router_awaiting_email(self):
        router = TelegramRouter(FakeUserStore())
        router.handleStart("user-1")

        response = router.handleText("user-1", "hello", datetime.now(timezone.utc))

        self.assertIn("valid email", response.lower())
        self.assertTrue(router.awaitingEmail["user-1"])

    def test_text_not_awaiting_email_returns_fixed_help_response(self):
        router = TelegramRouter(FakeUserStore())

        response = router.handleText("user-1", "hello", datetime.now(timezone.utc))

        self.assertIn("image", response.lower())

    def test_image_upload_without_registered_email_prompts_for_email(self):
        router = TelegramRouter(FakeUserStore())

        response = router.handleImageUpload("new-user")

        self.assertIn("email", response.lower())
        self.assertTrue(router.awaitingEmail["new-user"])

    def test_image_upload_with_registered_email_is_accepted(self):
        router = TelegramRouter(FakeUserStore())

        response = router.handleImageUpload("registered")

        self.assertIn("accepted", response.lower())

    def test_unsupported_upload_returns_fixed_image_only_message(self):
        router = TelegramRouter(FakeUserStore())

        response = router.handleUnsupportedUpload()

        self.assertIn("image", response.lower())


if __name__ == "__main__":
    unittest.main()
