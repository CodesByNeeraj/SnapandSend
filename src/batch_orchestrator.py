"""Deterministic processing of one closed photo batch."""

from typing import Any

from langfuse import get_client, observe


class BatchOrchestrator:
    """Coordinates extraction, curation, and one email delivery."""

    def __init__(self, visionExtractor: Any, notesCurator: Any, emailSender: Any):
        self.visionExtractor = visionExtractor
        self.notesCurator = notesCurator
        self.emailSender = emailSender

    @observe(name="process-photo-batch", capture_input=False, capture_output=False)
    async def processBatch(
        self,
        recipientEmail: str,
        imageBytes: list[bytes],
    ) -> str | None:
        """Process images in order and send one email for curated notes."""

        # capture_input/output are disabled above so the trace never records
        # raw photo bytes or the recipient email; only the photo count and a
        # delivery outcome are attached explicitly below.
        get_client().update_current_span(input={"photoCount": len(imageBytes)})

        extractedDocuments = []
        for image in imageBytes:
            document = await self.visionExtractor.extractDocument(image)
            extractedDocuments.append(document)

        curatedNotes = await self.notesCurator.curateNotes(extractedDocuments)
        if not curatedNotes.documents:
            get_client().update_current_span(output={"emailSent": False})
            return None

        emailId = self.emailSender.sendNotesEmail(recipientEmail, curatedNotes)
        get_client().update_current_span(output={"emailSent": True})
        return emailId
