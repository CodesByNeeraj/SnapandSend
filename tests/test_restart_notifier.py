import unittest

from src.restart_notifier import REUPLOAD_AFTER_RESTART_MESSAGE, RestartNotifier


class FakeUserStore:
    def __init__(self, pendingUserIds):
        self.pendingUserIds = pendingUserIds
        self.pendingClears = []

    def getUserIdsWithPendingBatch(self):
        return self.pendingUserIds

    def clearBatchPending(self, userId):
        self.pendingClears.append(userId)


class FakeBot:
    def __init__(self):
        self.sentMessages = []

    async def send_message(self, chat_id, text):
        self.sentMessages.append((chat_id, text))


class RestartNotifierTests(unittest.IsolatedAsyncioTestCase):
    async def test_notify_lost_batches_messages_and_clears_each_pending_user(self):
        userStore = FakeUserStore(["user-1", "user-2"])
        bot = FakeBot()
        notifier = RestartNotifier(bot, userStore)

        count = await notifier.notifyLostBatches()

        self.assertEqual(count, 2)
        self.assertEqual(
            bot.sentMessages,
            [
                ("user-1", REUPLOAD_AFTER_RESTART_MESSAGE),
                ("user-2", REUPLOAD_AFTER_RESTART_MESSAGE),
            ],
        )
        self.assertEqual(userStore.pendingClears, ["user-1", "user-2"])

    async def test_notify_lost_batches_does_nothing_when_no_users_pending(self):
        userStore = FakeUserStore([])
        bot = FakeBot()
        notifier = RestartNotifier(bot, userStore)

        count = await notifier.notifyLostBatches()

        self.assertEqual(count, 0)
        self.assertEqual(bot.sentMessages, [])
        self.assertEqual(userStore.pendingClears, [])


if __name__ == "__main__":
    unittest.main()
