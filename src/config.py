"""Runtime configuration loaded from environment variables."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from src.constants import AWS_REGION, DEFAULT_OPENAI_MODEL, DEFAULT_USERS_TABLE_NAME


class ConfigurationError(ValueError):
    """Raised when required application configuration is missing."""


@dataclass(frozen=True)
class Settings:
    """Validated settings needed to construct application integrations."""

    telegramBotToken: str
    openaiApiKey: str
    resendApiKey: str
    emailEncryptionKey: str
    awsRegion: str
    usersTableName: str
    resendFromEmail: str
    openaiModel: str

    @classmethod
    def fromEnvironment(cls) -> "Settings":
        """Load and validate settings from the process environment."""

        load_dotenv()
        requiredValues = {
            "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN"),
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            "RESEND_API_KEY": os.getenv("RESEND_API_KEY"),
            "EMAIL_ENCRYPTION_KEY": os.getenv("EMAIL_ENCRYPTION_KEY"),
            "RESEND_FROM_EMAIL": os.getenv("RESEND_FROM_EMAIL"),
        }
        missingValues = [
            name for name, value in requiredValues.items() if not value
        ]
        if missingValues:
            missingNames = ", ".join(missingValues)
            raise ConfigurationError(
                f"Missing required environment variables: {missingNames}"
            )

        return cls(
            telegramBotToken=requiredValues["TELEGRAM_BOT_TOKEN"],
            openaiApiKey=requiredValues["OPENAI_API_KEY"],
            resendApiKey=requiredValues["RESEND_API_KEY"],
            emailEncryptionKey=requiredValues["EMAIL_ENCRYPTION_KEY"],
            awsRegion=os.getenv("AWS_DEFAULT_REGION", AWS_REGION),
            usersTableName=os.getenv("USERS_TABLE_NAME", DEFAULT_USERS_TABLE_NAME),
            resendFromEmail=requiredValues["RESEND_FROM_EMAIL"],
            openaiModel=os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
        )
