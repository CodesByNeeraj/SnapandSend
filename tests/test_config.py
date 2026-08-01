import os
import unittest
from unittest.mock import patch

from src.config import ConfigurationError, Settings
from src.constants import (
    BATCH_INACTIVITY_SECONDS,
    DAILY_PHOTO_LIMIT,
    MAX_BATCH_PHOTOS,
    TELEGRAM_MAX_FILE_BYTES,
)


class SettingsTests(unittest.TestCase):
    def test_prd_limits_are_named_constants(self):
        self.assertEqual(BATCH_INACTIVITY_SECONDS, 180)
        self.assertEqual(DAILY_PHOTO_LIMIT, 30)
        self.assertEqual(MAX_BATCH_PHOTOS, 15)
        self.assertEqual(TELEGRAM_MAX_FILE_BYTES, 20 * 1024 * 1024)

    def test_settings_load_required_values_from_environment(self):
        environment = {
            "TELEGRAM_BOT_TOKEN": "telegram-token",
            "OPENAI_API_KEY": "openai-key",
            "RESEND_API_KEY": "resend-key",
            "KMS_KEY_ID": "alias/snap-and-send-email",
            "AWS_DEFAULT_REGION": "ap-southeast-1",
            "USERS_TABLE_NAME": "users",
            "RESEND_FROM_EMAIL": "notes@example.com",
            "OPENAI_MODEL": "gpt-5.6-terra",
            "LANGFUSE_PUBLIC_KEY": "pk-lf-test",
            "LANGFUSE_SECRET_KEY": "sk-lf-test",
            "LANGFUSE_HOST": "https://jp.cloud.langfuse.com",
        }

        with patch.dict(os.environ, environment, clear=True):
            settings = Settings.fromEnvironment()

        self.assertEqual(settings.telegramBotToken, "telegram-token")
        self.assertEqual(settings.openaiModel, "gpt-5.6-terra")
        self.assertEqual(settings.awsRegion, "ap-southeast-1")
        self.assertEqual(settings.kmsKeyId, "alias/snap-and-send-email")
        self.assertEqual(settings.langfusePublicKey, "pk-lf-test")
        self.assertEqual(settings.langfuseSecretKey, "sk-lf-test")
        self.assertEqual(settings.langfuseHost, "https://jp.cloud.langfuse.com")

    def test_settings_reject_missing_required_values(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("src.config.load_dotenv"):
                with self.assertRaises(ConfigurationError):
                    Settings.fromEnvironment()


if __name__ == "__main__":
    unittest.main()
