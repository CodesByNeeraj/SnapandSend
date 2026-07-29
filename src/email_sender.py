"""Email note rendering and delivery through an injected Resend client."""

from typing import Any

from src.notes_curator import CuratedNotes

EMAIL_SUBJECT = "Your Snap&Send notes"


def renderEmailBody(notes: CuratedNotes) -> str:
    """Render curated notes as ordered plain-text Markdown."""

    sections = []
    for document in notes.documents:
        bullets = "\n".join(f"- {bullet}" for bullet in document.bullets)
        sections.append(f"## {document.title}\n{bullets}".rstrip())
    return "# Snap&Send notes\n\n" + "\n\n".join(sections)


class EmailSender:
    """Sends one completed note to one registered email address."""

    def __init__(self, client: Any, fromEmail: str):
        self.client = client
        self.fromEmail = fromEmail

    def sendNotesEmail(self, recipientEmail: str, notes: CuratedNotes) -> str | None:
        """Send notes and return the provider's message identifier."""

        if not notes.documents:
            return None

        response = self.client.send(
            {
                "from": self.fromEmail,
                "to": [recipientEmail],
                "subject": EMAIL_SUBJECT,
                "text": renderEmailBody(notes),
            }
        )
        return response["id"]
