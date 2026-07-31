"""Notifies users whose batch was lost to a bot crash or restart."""

from typing import Any

REUPLOAD_AFTER_RESTART_MESSAGE = (
    "Sorry, I restarted and lost your in-progress batch. Please resend your photos."
)


class RestartNotifier:
    """Messages and clears every user left with an unresolved pending batch."""

    def __init__(self, bot: Any, userStore: Any):
        self.bot = bot
        self.userStore = userStore

    async def notifyLostBatches(self) -> int:
        """Message each user with a pending batch and clear their flag."""

        userIds = self.userStore.getUserIdsWithPendingBatch()
        for userId in userIds:
            await self.bot.send_message(
                chat_id=userId, text=REUPLOAD_AFTER_RESTART_MESSAGE
            )
            self.userStore.clearBatchPending(userId)
        return len(userIds)
