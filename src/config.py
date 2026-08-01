"""Runtime configuration loaded from environment variables."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from src.constants import AWS_REGION
from src.constants import DEFAULT_OPENAI_MODEL
from src.constants import DEFAULT_USERS_TABLE_NAME


class ConfigurationError(ValueError):
    """Raised when required application configuration is missing."""


@dataclass(frozen=True)
class Settings:
    """Validated settings needed to construct application integrations."""

    telegramBotToken: str
    openaiApiKey: str
    resendApiKey: str
    kmsKeyId: str
    awsRegion: str
    usersTableName: str
    resendFromEmail: str
    openaiModel: str
    langfusePublicKey: str
    langfuseSecretKey: str
    langfuseHost: str

    @classmethod
    def fromEnvironment(cls) -> "Settings":
        """Load and validate settings from the process environment."""

        load_dotenv()
        requiredValues = {
            "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN"),
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            "RESEND_API_KEY": os.getenv("RESEND_API_KEY"),
            "KMS_KEY_ID": os.getenv("KMS_KEY_ID"),
            "RESEND_FROM_EMAIL": os.getenv("RESEND_FROM_EMAIL"),
            "LANGFUSE_PUBLIC_KEY": os.getenv("LANGFUSE_PUBLIC_KEY"),
            "LANGFUSE_SECRET_KEY": os.getenv("LANGFUSE_SECRET_KEY"),
            "LANGFUSE_HOST": os.getenv("LANGFUSE_HOST"),
        }
        configuredValues = requiredValues.items()
        missingValues = [name for name, value in configuredValues if not value]
        if missingValues:
            missingNames = ", ".join(missingValues)
            raise ConfigurationError(
                f"Missing required environment variables: {missingNames}"
            )

        defaultTableName = DEFAULT_USERS_TABLE_NAME
        usersTableName = os.getenv("USERS_TABLE_NAME", defaultTableName)
        return cls(
            telegramBotToken=requiredValues["TELEGRAM_BOT_TOKEN"],
            openaiApiKey=requiredValues["OPENAI_API_KEY"],
            resendApiKey=requiredValues["RESEND_API_KEY"],
            kmsKeyId=requiredValues["KMS_KEY_ID"],
            awsRegion=os.getenv("AWS_DEFAULT_REGION", AWS_REGION),
            usersTableName=usersTableName,
            resendFromEmail=requiredValues["RESEND_FROM_EMAIL"],
            openaiModel=os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
            langfusePublicKey=requiredValues["LANGFUSE_PUBLIC_KEY"],
            langfuseSecretKey=requiredValues["LANGFUSE_SECRET_KEY"],
            langfuseHost=requiredValues["LANGFUSE_HOST"],
        )
