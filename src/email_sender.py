"""Email note rendering and delivery through an injected Resend client."""

import html
from dataclasses import dataclass
from typing import Any

from src.notes_curator import CuratedNotes
from src.vision_extractor import ContentBlock

EMAIL_SUBJECT = "Your Snap&Send notes"

HTML_BODY_STYLE = "font-family: sans-serif; color: #1a1a1a; line-height: 1.5;"
HTML_HEADING_STYLE = "margin: 24px 0 8px;"
HTML_SUBHEADING_STYLE = "margin: 16px 0 4px;"
HTML_LIST_STYLE = "margin: 0 0 16px; padding-left: 20px;"
HTML_PARAGRAPH_STYLE = "margin: 0 0 16px;"
HTML_FLOWCHART_LINE_STYLE = "margin: 0 0 4px;"
FLOWCHART_INDENT_PX = 20
HTML_TABLE_STYLE = "border-collapse: collapse; margin: 0 0 16px;"
HTML_TABLE_CELL_STYLE = "border: 1px solid #ccc; padding: 4px 8px; text-align: left;"

FLOWCHART_ARROW = "→"


class EmailDeliveryError(RuntimeError):
    """Raised when Resend cannot deliver a completed notes email."""


@dataclass(frozen=True)
class FlowchartLine:
    """One rendered row of a flowchart: an indentation depth and its text."""

    depth: int
    text: str


def renderFlowchartLines(block: ContentBlock) -> list[FlowchartLine]:
    """Walk a flowchart's edges into ordered, indented, arrow-joined lines.

    A straight chain of unlabeled edges collapses onto one line
    ("A -> B -> C"). A node with more than one outgoing edge, or a labeled
    edge, starts a new indented line per branch, so decision points and
    labeled arrows stay visible instead of being flattened.
    """

    outgoing: dict[str, list] = {}
    hasIncoming: set[str] = set()
    for edge in block.edges:
        outgoing.setdefault(edge.source, []).append(edge)
        hasIncoming.add(edge.target)

    startNodes = [node for node in block.nodes if node not in hasIncoming]
    if not startNodes and block.nodes:
        startNodes = block.nodes[:1]

    lines: list[FlowchartLine] = []
    visited: set[str] = set()

    def walk(node: str, depth: int, prefix: str) -> None:
        if node in visited:
            lines.append(FlowchartLine(depth, prefix + node))
            return
        visited.add(node)
        edges = outgoing.get(node, [])
        if len(edges) == 1 and not edges[0].label:
            walk(edges[0].target, depth, f"{prefix}{node} {FLOWCHART_ARROW} ")
            return
        lines.append(FlowchartLine(depth, prefix + node))
        for edge in edges:
            branchPrefix = (
                f"-- {edge.label} --> " if edge.label else f"{FLOWCHART_ARROW} "
            )
            walk(edge.target, depth + 1, branchPrefix)

    for node in startNodes:
        if node not in visited:
            walk(node, 0, "")

    return lines


def renderContentBlockText(block: ContentBlock) -> str:
    """Render one content block as plain text."""

    if block.type == "heading":
        return f"### {block.text}"
    if block.type == "paragraph":
        return block.text
    if block.type == "bullets":
        return "\n".join(f"- {item}" for item in block.items)
    if block.type == "table":
        headerRow = f"| {' | '.join(block.headers)} |"
        separatorRow = f"| {' | '.join('---' for _ in block.headers)} |"
        dataRows = [f"| {' | '.join(row)} |" for row in block.rows]
        return "\n".join([headerRow, separatorRow, *dataRows])
    lines = renderFlowchartLines(block)
    return "\n".join(("  " * line.depth) + line.text for line in lines)


def renderContentBlockHtml(block: ContentBlock) -> str:
    """Render one content block as an HTML fragment."""

    if block.type == "heading":
        return f'<h3 style="{HTML_SUBHEADING_STYLE}">{html.escape(block.text)}</h3>'
    if block.type == "paragraph":
        return f'<p style="{HTML_PARAGRAPH_STYLE}">{html.escape(block.text)}</p>'
    if block.type == "bullets":
        items = "".join(f"<li>{html.escape(item)}</li>" for item in block.items)
        return f'<ul style="{HTML_LIST_STYLE}">{items}</ul>'
    if block.type == "table":
        headerCells = "".join(
            f'<th style="{HTML_TABLE_CELL_STYLE}">{html.escape(header)}</th>'
            for header in block.headers
        )
        bodyRows = "".join(
            "<tr>"
            + "".join(
                f'<td style="{HTML_TABLE_CELL_STYLE}">{html.escape(cell)}</td>'
                for cell in row
            )
            + "</tr>"
            for row in block.rows
        )
        return (
            f'<table style="{HTML_TABLE_STYLE}">'
            f"<thead><tr>{headerCells}</tr></thead>"
            f"<tbody>{bodyRows}</tbody>"
            "</table>"
        )
    rows = []
    for line in renderFlowchartLines(block):
        indent = FLOWCHART_INDENT_PX * line.depth
        style = f"{HTML_FLOWCHART_LINE_STYLE} margin-left: {indent}px;"
        rows.append(f'<p style="{style}">{html.escape(line.text)}</p>')
    return "".join(rows)


def renderEmailBody(notes: CuratedNotes) -> str:
    """Render curated notes as ordered plain-text Markdown.

    Kept as a plain-text fallback for email clients that cannot display
    HTML; renderEmailBodyHtml is what most recipients actually see.
    """

    sections = []
    for document in notes.documents:
        parts = [f"## {document.title}"]
        parts.extend(renderContentBlockText(block) for block in document.blocks)
        sections.append("\n\n".join(parts).rstrip())
    return "# Snap&Send notes\n\n" + "\n\n".join(sections)


def renderEmailBodyHtml(notes: CuratedNotes) -> str:
    """Render curated notes as a styled HTML email body."""

    sections = []
    for document in notes.documents:
        blockHtml = [renderContentBlockHtml(block) for block in document.blocks]
        sections.append(
            f'<h2 style="{HTML_HEADING_STYLE}">{html.escape(document.title)}</h2>'
            + "".join(blockHtml)
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
