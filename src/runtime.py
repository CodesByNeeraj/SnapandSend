"""Runtime construction of Snap&Send application components."""

from dataclasses import dataclass
from typing import Any

import boto3
import resend
from langfuse import Langfuse
from langfuse.openai import AsyncOpenAI

from src.batch_manager import BatchManager
from src.batch_orchestrator import BatchOrchestrator
from src.config import Settings
from src.email_sender import EmailSender
from src.expired_batch_processor import ExpiredBatchProcessor
from src.done_batch_router import DoneBatchRouter
from src.image_processor import prepareImage
from src.notes_curator import NotesCurator
from src.photo_batch_router import PhotoBatchRouter
from src.rate_limiter import RateLimiter
from src.telegram_router import TelegramRouter
from src.telegram_update_adapter import TelegramUpdateAdapter
from src.timeout_scheduler import TimeoutScheduler
from src.trace_masking import maskImageData
from src.user_store import KmsEmailEncryptor, UserStore
from src.vision_extractor import VisionExtractor


class ResendClient:
    """Adapts the Resend module to the EmailSender client boundary."""

    def __init__(self, apiKey: str):
        resend.api_key = apiKey

    def send(self, request: dict[str, Any]) -> dict[str, Any]:
        """Send one email through Resend."""

        return resend.Emails.send(request)


@dataclass(frozen=True)
class Runtime:
    """Application services constructed from validated settings."""

    telegramRouter: TelegramRouter
    telegramUpdateAdapter: TelegramUpdateAdapter
    timeoutScheduler: TimeoutScheduler
    userStore: UserStore


def buildRuntime(settings: Settings) -> Runtime:
    """Construct application services without making network requests."""

    dynamoResource = boto3.resource("dynamodb", region_name=settings.awsRegion)
    usersTable = dynamoResource.Table(settings.usersTableName)
    kmsClient = boto3.client("kms", region_name=settings.awsRegion)
    userStore = UserStore(usersTable, KmsEmailEncryptor(kmsClient, settings.kmsKeyId))
    Langfuse(
        public_key=settings.langfusePublicKey,
        secret_key=settings.langfuseSecretKey,
        host=settings.langfuseHost,
        mask=maskImageData,
    )
    openaiClient = AsyncOpenAI(api_key=settings.openaiApiKey)
    visionExtractor = VisionExtractor(openaiClient, settings.openaiModel)
    notesCurator = NotesCurator(openaiClient, settings.openaiModel)
    emailSender = EmailSender(
        ResendClient(settings.resendApiKey), settings.resendFromEmail
    )
    batchManager = BatchManager()
    batchOrchestrator = BatchOrchestrator(visionExtractor, notesCurator, emailSender)
    expiredBatchProcessor = ExpiredBatchProcessor(
        batchManager, userStore, batchOrchestrator
    )
    telegramRouter = TelegramRouter(userStore)
    photoBatchRouter = PhotoBatchRouter(
        RateLimiter(), batchManager, prepareImage, userStore
    )
    doneBatchRouter = DoneBatchRouter(batchManager, userStore, batchOrchestrator)
    return Runtime(
        telegramRouter=telegramRouter,
        telegramUpdateAdapter=TelegramUpdateAdapter(
            telegramRouter, photoBatchRouter, doneBatchRouter
        ),
        timeoutScheduler=TimeoutScheduler(expiredBatchProcessor),
        userStore=userStore,
    )
