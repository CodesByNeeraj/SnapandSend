import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from src.email_sender import (
    EmailDeliveryError,
    EmailSender,
    buildEmailSubject,
    renderEmailBody,
    renderEmailBodyHtml,
)
from src.notes_curator import CuratedDocument, CuratedNotes
from src.vision_extractor import ContentBlock, FlowchartEdge


def bulletsBlock(*items: str) -> list[ContentBlock]:
    return [ContentBlock(type="bullets", items=list(items))]


def paragraphBlock(text: str) -> list[ContentBlock]:
    return [ContentBlock(type="paragraph", text=text)]


def flowchartBlock(nodes: list[str], edges: list[tuple[str, str, str]]) -> ContentBlock:
    return ContentBlock(
        type="flowchart",
        nodes=nodes,
        edges=[FlowchartEdge(source=s, target=t, label=label) for s, t, label in edges],
    )


def tableBlock(headers: list[str], rows: list[list[str]]) -> ContentBlock:
    return ContentBlock(type="table", headers=headers, rows=rows)


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
                CuratedDocument(
                    title="First slide", blocks=bulletsBlock("First point")
                ),
                CuratedDocument(
                    title="Second slide", blocks=bulletsBlock("Second point")
                ),
            ]
        )

        body = renderEmailBody(notes)

        self.assertEqual(
            body,
            "# Snap&Send notes\n\n## First slide\n\n- First point\n\n"
            "## Second slide\n\n- Second point",
        )

    def test_render_email_body_keeps_paragraph_blocks_as_prose(self):
        notes = CuratedNotes(
            documents=[
                CuratedDocument(
                    title="Whiteboard", blocks=paragraphBlock("Free-form notes.")
                )
            ]
        )

        body = renderEmailBody(notes)

        self.assertEqual(body, "# Snap&Send notes\n\n## Whiteboard\n\nFree-form notes.")

    def test_render_email_body_renders_heading_before_its_paragraph(self):
        notes = CuratedNotes(
            documents=[
                CuratedDocument(
                    title="Prefill vs Decode",
                    blocks=[
                        ContentBlock(type="heading", text="The Decode Phase"),
                        ContentBlock(
                            type="paragraph",
                            text="Compute-Bound: Faster GPUs directly improve "
                            "token throughput",
                        ),
                    ],
                )
            ]
        )

        body = renderEmailBody(notes)

        self.assertEqual(
            body,
            "# Snap&Send notes\n\n## Prefill vs Decode\n\n### The Decode Phase\n\n"
            "Compute-Bound: Faster GPUs directly improve token throughput",
        )

    def test_render_email_body_html_renders_heading_as_h3(self):
        notes = CuratedNotes(
            documents=[
                CuratedDocument(
                    title="Whiteboard",
                    blocks=[ContentBlock(type="heading", text="Sub <heading> & more")],
                )
            ]
        )

        html = renderEmailBodyHtml(notes)

        self.assertIn("<h3", html)
        self.assertIn("Sub &lt;heading&gt; &amp; more</h3>", html)

    def test_render_email_body_preserves_mixed_block_order(self):
        notes = CuratedNotes(
            documents=[
                CuratedDocument(
                    title="Mixed slide",
                    blocks=[
                        ContentBlock(type="paragraph", text="Intro."),
                        ContentBlock(type="bullets", items=["First", "Second"]),
                    ],
                )
            ]
        )

        body = renderEmailBody(notes)

        self.assertEqual(
            body,
            "# Snap&Send notes\n\n## Mixed slide\n\nIntro.\n\n- First\n- Second",
        )

    def test_render_email_body_html_escapes_content_and_formats_lists(self):
        notes = CuratedNotes(
            documents=[
                CuratedDocument(
                    title="First <slide>", blocks=bulletsBlock("A & B", "point")
                ),
            ]
        )

        html = renderEmailBodyHtml(notes)

        self.assertIn("First &lt;slide&gt;</h2>", html)
        self.assertIn("<li>A &amp; B</li>", html)
        self.assertIn("<li>point</li>", html)
        self.assertNotIn("<slide>", html)

    def test_render_email_body_html_renders_paragraph_as_p_tag(self):
        notes = CuratedNotes(
            documents=[
                CuratedDocument(
                    title="Whiteboard", blocks=paragraphBlock("Free & form <notes>")
                )
            ]
        )

        html = renderEmailBodyHtml(notes)

        self.assertIn("<p", html)
        self.assertIn("Free &amp; form &lt;notes&gt;</p>", html)
        self.assertNotIn("<ul", html)

    def test_render_email_body_collapses_linear_flowchart_into_one_line(self):
        block = flowchartBlock(
            ["Start", "Run tests", "Deploy"],
            [("Start", "Run tests", ""), ("Run tests", "Deploy", "")],
        )
        notes = CuratedNotes(
            documents=[CuratedDocument(title="Deploy process", blocks=[block])]
        )

        body = renderEmailBody(notes)

        self.assertEqual(
            body,
            "# Snap&Send notes\n\n## Deploy process\n\nStart → Run tests → Deploy",
        )

    def test_render_email_body_indents_branching_flowchart(self):
        block = flowchartBlock(
            ["Submit", "Review", "Approve", "Reject"],
            [
                ("Submit", "Review", ""),
                ("Review", "Approve", "yes"),
                ("Review", "Reject", "no"),
            ],
        )
        notes = CuratedNotes(
            documents=[CuratedDocument(title="Approval", blocks=[block])]
        )

        body = renderEmailBody(notes)

        self.assertEqual(
            body,
            "# Snap&Send notes\n\n## Approval\n\nSubmit → Review\n"
            "  -- yes --> Approve\n  -- no --> Reject",
        )

    def test_render_email_body_flowchart_survives_a_cycle(self):
        block = flowchartBlock(["A", "B"], [("A", "B", ""), ("B", "A", "")])
        notes = CuratedNotes(documents=[CuratedDocument(title="Loop", blocks=[block])])

        body = renderEmailBody(notes)

        self.assertEqual(body, "# Snap&Send notes\n\n## Loop\n\nA → B → A")

    def test_render_email_body_html_indents_branching_flowchart(self):
        block = flowchartBlock(
            ["Submit", "Review", "Approve", "Reject"],
            [
                ("Submit", "Review", ""),
                ("Review", "Approve", "yes"),
                ("Review", "Reject", "no"),
            ],
        )
        notes = CuratedNotes(
            documents=[CuratedDocument(title="Approval", blocks=[block])]
        )

        html = renderEmailBodyHtml(notes)

        self.assertIn("Submit → Review", html)
        self.assertIn("-- yes --&gt; Approve", html)
        self.assertIn("-- no --&gt; Reject", html)
        self.assertIn("margin-left: 20px", html)

    def test_render_email_body_renders_table_as_pipe_rows(self):
        block = tableBlock(["Region", "Growth"], [["US", "302%"], ["China", "443%"]])
        notes = CuratedNotes(
            documents=[CuratedDocument(title="Growth", blocks=[block])]
        )

        body = renderEmailBody(notes)

        self.assertEqual(
            body,
            "# Snap&Send notes\n\n## Growth\n\n"
            "| Region | Growth |\n| --- | --- |\n"
            "| US | 302% |\n| China | 443% |",
        )

    def test_render_email_body_html_renders_table_element(self):
        block = tableBlock(
            ["Region", "Growth"], [["US", "302%"], ["China & co", "443%"]]
        )
        notes = CuratedNotes(
            documents=[CuratedDocument(title="Growth", blocks=[block])]
        )

        html = renderEmailBodyHtml(notes)

        self.assertIn("<table", html)
        self.assertIn("<th", html)
        self.assertIn("Region", html)
        self.assertIn("<td", html)
        self.assertIn("China &amp; co", html)

    def test_build_email_subject_includes_the_date_in_singapore_timezone(self):
        # 11pm UTC on Jan 1 is already Jan 2 in Singapore (UTC+8).
        now = datetime(2026, 1, 1, 23, 0, tzinfo=ZoneInfo("UTC"))

        subject = buildEmailSubject(now)

        self.assertEqual(subject, "Your Snap&Send notes - 02 Jan 2026")

    def test_send_notes_sends_one_email_to_registered_address(self):
        client = FakeEmailClient()
        sender = EmailSender(client, "notes@example.com")

        notes = CuratedNotes(
            documents=[
                CuratedDocument(title="Slide title", blocks=bulletsBlock("First point"))
            ]
        )
        result = sender.sendNotesEmail("person@example.com", notes)

        self.assertEqual(result, "email-1")
        self.assertEqual(len(client.requests), 1)
        self.assertEqual(client.requests[0]["to"], ["person@example.com"])
        self.assertIn("Slide title", client.requests[0]["text"])
        self.assertIn("Slide title</h2>", client.requests[0]["html"])
        self.assertIn("<li>First point</li>", client.requests[0]["html"])
        self.assertTrue(
            client.requests[0]["subject"].startswith("Your Snap&Send notes - ")
        )

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
            documents=[
                CuratedDocument(title="Slide title", blocks=bulletsBlock("First point"))
            ]
        )

        with self.assertRaises(EmailDeliveryError):
            sender.sendNotesEmail("person@example.com", notes)


if __name__ == "__main__":
    unittest.main()
