"""Deterministic processing of one closed photo batch."""

from typing import Any


class BatchOrchestrator:
    """Coordinates extraction, curation, and one email delivery."""

    def __init__(self, visionExtractor: Any, notesCurator: Any, emailSender: Any):
        self.visionExtractor = visionExtractor
        self.notesCurator = notesCurator
        self.emailSender = emailSender

    async def processBatch(
        self,
        recipientEmail: str,
        imageBytes: list[bytes],
    ) -> str | None:
        """Process images in order and send one email for curated notes."""

        extractedDocuments = []
        for image in imageBytes:
            document = await self.visionExtractor.extractDocument(image)
            extractedDocuments.append(document)

        curatedNotes = await self.notesCurator.curateNotes(extractedDocuments)
        if not curatedNotes.documents:
            return None

        return self.emailSender.sendNotesEmail(recipientEmail, curatedNotes)
