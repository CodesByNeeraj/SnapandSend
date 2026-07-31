"""Encrypted email persistence for the DynamoDB users table."""

import base64
from datetime import datetime, timezone
from typing import Any

from boto3.dynamodb.conditions import Attr

KMS_EMAIL_ENCRYPTION_PURPOSE = "snap-and-send-user-email"


def createEncryptionContext(userId: str) -> dict[str, str]:
    """Bind KMS ciphertext to the Telegram user it belongs to."""

    return {
        "purpose": KMS_EMAIL_ENCRYPTION_PURPOSE,
        "telegram_user_id": userId,
    }


class KmsEmailEncryptor:
    """Encrypts and decrypts email addresses through AWS KMS."""

    def __init__(self, kmsClient: Any, keyId: str):
        self.kmsClient = kmsClient
        self.keyId = keyId

    def encryptEmail(self, userId: str, email: str) -> str:
        """Return base64-encoded KMS ciphertext."""

        response = self.kmsClient.encrypt(
            KeyId=self.keyId,
            Plaintext=email.encode(),
            EncryptionContext=createEncryptionContext(userId),
        )
        return base64.b64encode(response["CiphertextBlob"]).decode("ascii")

    def decryptEmail(self, userId: str, encryptedEmail: str) -> str:
        """Decrypt a base64-encoded KMS ciphertext."""

        response = self.kmsClient.decrypt(
            KeyId=self.keyId,
            CiphertextBlob=base64.b64decode(encryptedEmail),
            EncryptionContext=createEncryptionContext(userId),
        )
        return response["Plaintext"].decode()


class UserStore:
    """Reads and writes encrypted user email records."""

    def __init__(self, usersTable: Any, emailEncryptor: KmsEmailEncryptor):
        self.usersTable = usersTable
        self.emailEncryptor = emailEncryptor

    def saveEmail(
        self,
        userId: str,
        email: str,
        createdAt: datetime | None = None,
    ) -> None:
        """Store an encrypted email address and creation timestamp."""

        timestamp = createdAt or datetime.now(timezone.utc)
        self.usersTable.put_item(
            Item={
                "telegram_user_id": userId,
                "email": self.emailEncryptor.encryptEmail(userId, email),
                "created_at": timestamp.isoformat(),
            }
        )

    def getEmail(self, userId: str) -> str | None:
        """Return a user's decrypted email, or ``None`` if not registered."""

        response = self.usersTable.get_item(Key={"telegram_user_id": userId})
        item = response.get("Item")
        if not item:
            return None
        return self.emailEncryptor.decryptEmail(userId, item["email"])

    def markBatchPending(self, userId: str) -> None:
        """Flag that a user has an unclosed batch held only in process memory."""

        self._setPendingBatch(userId, True)

    def clearBatchPending(self, userId: str) -> None:
        """Clear a user's pending batch flag once it is closed or resolved."""

        self._setPendingBatch(userId, False)

    def _setPendingBatch(self, userId: str, pending: bool) -> None:
        self.usersTable.update_item(
            Key={"telegram_user_id": userId},
            UpdateExpression="SET pending_batch = :value",
            ExpressionAttributeValues={":value": pending},
        )

    def getUserIdsWithPendingBatch(self) -> list[str]:
        """Return user ids left with a pending batch by a crash or restart."""

        response = self.usersTable.scan(FilterExpression=Attr("pending_batch").eq(True))
        return [item["telegram_user_id"] for item in response.get("Items", [])]
