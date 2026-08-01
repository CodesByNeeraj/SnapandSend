import unittest
from unittest.mock import patch

from src.config import Settings
from src.runtime import buildRuntime
from src.trace_masking import maskImageData


class FakeDynamoResource:
    def Table(self, name):
        return object()


class RuntimeTests(unittest.TestCase):
    def test_build_runtime_constructs_telegram_services_without_network(self):
        settings = Settings(
            "telegram",
            "openai",
            "resend",
            "kms",
            "region",
            "users",
            "from@example.com",
            "model",
            "langfuse-public",
            "langfuse-secret",
            "https://jp.cloud.langfuse.com",
        )
        with patch("src.runtime.boto3.resource", return_value=FakeDynamoResource()):
            with patch("src.runtime.boto3.client", return_value=object()):
                with patch("src.runtime.AsyncOpenAI"):
                    with patch("src.runtime.ResendClient"):
                        with patch("src.runtime.Langfuse") as langfuse:
                            runtime = buildRuntime(settings)
        self.assertIsNotNone(runtime.telegramUpdateAdapter)
        self.assertIsNotNone(runtime.timeoutScheduler)
        langfuse.assert_called_once_with(
            public_key="langfuse-public",
            secret_key="langfuse-secret",
            host="https://jp.cloud.langfuse.com",
            mask=maskImageData,
        )


if __name__ == "__main__":
    unittest.main()
