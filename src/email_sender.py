"""Email note rendering and delivery through an injected Resend client."""

import html
from typing import Any

from src.notes_curator import CuratedNotes

EMAIL_SUBJECT = "Your Snap&Send notes"

HTML_BODY_STYLE = "font-family: sans-serif; color: #1a1a1a; line-height: 1.5;"
HTML_HEADING_STYLE = "margin: 24px 0 8px;"
HTML_LIST_STYLE = "margin: 0 0 16px; padding-left: 20px;"


class EmailDeliveryError(RuntimeError):
    """Raised when Resend cannot deliver a completed notes email."""


def renderEmailBody(notes: CuratedNotes) -> str:
    """Render curated notes as ordered plain-text Markdown.

    Kept as a plain-text fallback for email clients that cannot display
    HTML; renderEmailBodyHtml is what most recipients actually see.
    """

    sections = []
    for document in notes.documents:
        bullets = "\n".join(f"- {bullet}" for bullet in document.bullets)
        sections.append(f"## {document.title}\n{bullets}".rstrip())
    return "# Snap&Send notes\n\n" + "\n\n".join(sections)


def renderEmailBodyHtml(notes: CuratedNotes) -> str:
    """Render curated notes as a styled HTML email body."""

    sections = []
    for document in notes.documents:
        bullets = "".join(
            f"<li>{html.escape(bullet)}</li>" for bullet in document.bullets
        )
        sections.append(
            f'<h2 style="{HTML_HEADING_STYLE}">{html.escape(document.title)}</h2>'
            f'<ul style="{HTML_LIST_STYLE}">{bullets}</ul>'
        )
    heading = f'<h1 style="{HTML_HEADING_STYLE}">Snap&amp;Send notes</h1>'
    return f'<div style="{HTML_BODY_STYLE}">' + heading + "".join(sections) + "</div>"


class EmailSender:
    """Sends one completed note to one registered email address."""

    def __init__(self, client: Any, fromEmail: str):
        self.client = client
        self.fromEmail = fromEmail

    def sendNotesEmail(self, recipientEmail: str, notes: CuratedNotes) -> str | None:
        """Send notes and return the provider's message identifier."""

        if not notes.documents:
            return None

        try:
            response = self.client.send(
                {
                    "from": self.fromEmail,
                    "to": [recipientEmail],
                    "subject": EMAIL_SUBJECT,
                    "text": renderEmailBody(notes),
                    "html": renderEmailBodyHtml(notes),
                }
            )
        except RuntimeError as error:
            raise EmailDeliveryError("Resend delivery failed") from error
        return response["id"]
