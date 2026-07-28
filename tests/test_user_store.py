import unittest
from datetime import datetime, timezone

from src.user_store import KmsEmailEncryptor, UserStore


class FakeKmsClient:
    def __init__(self):
        self.encryptRequests = []
        self.decryptRequests = []

    def encrypt(self, **kwargs):
        self.encryptRequests.append(kwargs)
        return {"CiphertextBlob": b"encrypted:" + kwargs["Plaintext"]}

    def decrypt(self, **kwargs):
        self.decryptRequests.append(kwargs)
        return {"Plaintext": kwargs["CiphertextBlob"][10:]}


class FakeUsersTable:
    def __init__(self):
        self.items = {}

    def put_item(self, Item):
        self.items[Item["telegram_user_id"]] = Item

    def get_item(self, Key):
        item = self.items.get(Key["telegram_user_id"])
        return {"Item": item} if item else {}


class UserStoreTests(unittest.TestCase):
    def test_encryptor_round_trips_email_without_plaintext_storage(self):
        kmsClient = FakeKmsClient()
        encryptor = KmsEmailEncryptor(kmsClient, "kms-key-id")
        userId = "telegram-user-1"
        email = "person@example.com"

        encryptedEmail = encryptor.encryptEmail(userId, email)
        decryptedEmail = encryptor.decryptEmail(userId, encryptedEmail)

        self.assertNotIn(email, encryptedEmail)
        self.assertEqual(decryptedEmail, email)
        expectedContext = {
            "purpose": "snap-and-send-user-email",
            "telegram_user_id": "telegram-user-1",
        }
        self.assertEqual(
            kmsClient.encryptRequests[0]["EncryptionContext"], expectedContext
        )
        self.assertEqual(
            kmsClient.decryptRequests[0]["EncryptionContext"], expectedContext
        )

    def test_user_store_saves_encrypted_email_and_reads_it_back(self):
        table = FakeUsersTable()
        encryptor = KmsEmailEncryptor(FakeKmsClient(), "kms-key-id")
        store = UserStore(table, encryptor)
        createdAt = datetime(2026, 7, 28, tzinfo=timezone.utc)

        store.saveEmail("telegram-user-1", "person@example.com", createdAt)

        storedItem = table.items["telegram-user-1"]
        storedEmail = store.getEmail("telegram-user-1")
        self.assertNotIn("person@example.com", storedItem["email"])
        self.assertEqual(storedEmail, "person@example.com")
        self.assertEqual(storedItem["created_at"], createdAt.isoformat())

    def test_user_store_returns_none_for_unknown_user(self):
        store = UserStore(
            FakeUsersTable(), KmsEmailEncryptor(FakeKmsClient(), "kms-key-id")
        )

        self.assertIsNone(store.getEmail("missing-user"))

    def test_user_store_replaces_email_for_existing_user(self):
        table = FakeUsersTable()
        encryptor = KmsEmailEncryptor(FakeKmsClient(), "kms-key-id")
        store = UserStore(table, encryptor)
        firstCreatedAt = datetime(2026, 7, 28, tzinfo=timezone.utc)
        updatedAt = datetime(2026, 7, 29, tzinfo=timezone.utc)

        store.saveEmail("telegram-user-1", "first@example.com", firstCreatedAt)
        store.saveEmail("telegram-user-1", "updated@example.com", updatedAt)

        updatedEmail = store.getEmail("telegram-user-1")
        self.assertEqual(updatedEmail, "updated@example.com")
        self.assertEqual(
            table.items["telegram-user-1"]["created_at"], updatedAt.isoformat()
        )


if __name__ == "__main__":
    unittest.main()
