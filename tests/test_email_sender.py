import unittest

from src.email_sender import EmailSender, renderEmailBody
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

    def test_send_notes_does_not_call_provider_for_empty_notes(self):
        client = FakeEmailClient()
        sender = EmailSender(client, "notes@example.com")

        result = sender.sendNotesEmail("person@example.com", CuratedNotes(documents=[]))

        self.assertIsNone(result)
        self.assertEqual(client.requests, [])


if __name__ == "__main__":
    unittest.main()
