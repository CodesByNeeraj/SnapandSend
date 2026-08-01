import unittest

from src.email_sender import (
    EmailDeliveryError,
    EmailSender,
    renderEmailBody,
    renderEmailBodyHtml,
)
from src.notes_curator import CuratedDocument, CuratedNotes


class FakeEmailClient:
    def __init__(self):
        self.requests = []

    def send(self, request):
        self.requests.append(request)
        return {"id": "email-1"}


class EmailSenderTests(unittest.TestCase):
    def test_render_email_body_formats_curated_documents_in_order(self):
        notes = CuratedNotes(
            documents=[
                CuratedDocument(title="First slide", bullets=["First point"]),
                CuratedDocument(title="Second slide", bullets=["Second point"]),
            ]
        )

        body = renderEmailBody(notes)

        self.assertEqual(
            body,
            "# Snap&Send notes\n\n## First slide\n- First point\n\n"
            "## Second slide\n- Second point",
        )

    def test_render_email_body_html_escapes_content_and_formats_lists(self):
        notes = CuratedNotes(
            documents=[
                CuratedDocument(title="First <slide>", bullets=["A & B", "point"]),
            ]
        )

        html = renderEmailBodyHtml(notes)

        self.assertIn("First &lt;slide&gt;</h2>", html)
        self.assertIn("<li>A &amp; B</li>", html)
        self.assertIn("<li>point</li>", html)
        self.assertNotIn("<slide>", html)

    def test_send_notes_sends_one_email_to_registered_address(self):
        client = FakeEmailClient()
        sender = EmailSender(client, "notes@example.com")

        notes = CuratedNotes(
            documents=[CuratedDocument(title="Slide title", bullets=["First point"])]
        )
        result = sender.sendNotesEmail("person@example.com", notes)

        self.assertEqual(result, "email-1")
        self.assertEqual(len(client.requests), 1)
        self.assertEqual(client.requests[0]["to"], ["person@example.com"])
        self.assertIn("Slide title", client.requests[0]["text"])
        self.assertIn("Slide title</h2>", client.requests[0]["html"])
        self.assertIn("<li>First point</li>", client.requests[0]["html"])

    def test_send_notes_does_not_call_provider_for_empty_notes(self):
        client = FakeEmailClient()
        sender = EmailSender(client, "notes@example.com")

        result = sender.sendNotesEmail("person@example.com", CuratedNotes(documents=[]))

        self.assertIsNone(result)
        self.assertEqual(client.requests, [])

    def test_send_notes_propagates_resend_failure(self):
        client = FakeEmailClient()
        client.send = lambda request: (_ for _ in ()).throw(RuntimeError("failed"))
        sender = EmailSender(client, "notes@example.com")
        notes = CuratedNotes(
            documents=[CuratedDocument(title="Slide title", bullets=["First point"])]
        )

        with self.assertRaises(EmailDeliveryError):
            sender.sendNotesEmail("person@example.com", notes)


if __name__ == "__main__":
    unittest.main()
