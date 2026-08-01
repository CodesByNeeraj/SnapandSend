"""Async OpenAI note curation for extracted documents."""

import json
from dataclasses import asdict
from dataclasses import dataclass
from typing import Any

from openai import APIError

from src.vision_extractor import CONTENT_BLOCK_SCHEMA, ContentBlock, ExtractedDocument
from src.vision_extractor import parseContentBlocks

CURATION_PROMPT = """
Combine these extracted documents into concise notes. Omit near-duplicate
documents, preserve the source order of distinct documents, and do not add or
rewrite facts. Return each kept document with its title and its blocks,
preserving whether each block was a heading, a paragraph, a bullet list, a
flowchart, or a table, including a flowchart's nodes and edges or a table's
headers and rows exactly as given.
""".strip()
CURATION_ATTEMPTS = 2
CURATION_RESPONSE_FORMAT = {
    "type": "json_schema",
    "name": "curated_notes",
    "description": "Ordered, deduplicated notes from extracted documents.",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "documents": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "blocks": {"type": "array", "items": CONTENT_BLOCK_SCHEMA},
                    },
                    "required": ["title", "blocks"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["documents"],
        "additionalProperties": False,
    },
}


class NotesCurationError(RuntimeError):
    """Raised when note curation fails or returns invalid data."""


@dataclass(frozen=True)
class CuratedDocument:
    """One curated document ready for email rendering."""

    title: str
    blocks: list[ContentBlock]


@dataclass(frozen=True)
class CuratedNotes:
    """Ordered documents after curation."""

    documents: list[CuratedDocument]


class NotesCurator:
    """Calls the injected async OpenAI client to curate extracted documents."""

    def __init__(self, client: Any, model: str):
        self.client = client
        self.model = model

    async def curateNotes(self, documents: list[ExtractedDocument]) -> CuratedNotes:
        """Curate readable documents, retrying one failed provider call."""

        readableDocuments = [
            asdict(document) for document in documents if document.status == "readable"
        ]
        if not readableDocuments:
            return CuratedNotes(documents=[])

        request = {
            "model": self.model,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": CURATION_PROMPT},
                        {"type": "input_text", "text": json.dumps(readableDocuments)},
                    ],
                }
            ],
            "text": {"format": CURATION_RESPONSE_FORMAT},
        }
        lastError: Exception | None = None
        for _ in range(CURATION_ATTEMPTS):
            try:
                response = await self.client.responses.create(**request)
                return parseCuratedNotes(response.output_text)
            except (APIError, TimeoutError) as error:
                lastError = error

        raise NotesCurationError(
            "OpenAI curation failed after one retry"
        ) from lastError


def parseCuratedNotes(outputText: str) -> CuratedNotes:
    """Parse and validate the OpenAI structured response."""

    try:
        output = json.loads(outputText)
    except json.JSONDecodeError as error:
        raise NotesCurationError("OpenAI curation returned invalid JSON") from error

    documents = output.get("documents") if isinstance(output, dict) else None
    if not isinstance(documents, list):
        raise NotesCurationError("OpenAI curation returned an invalid response")

    curatedDocuments = []
    for document in documents:
        title = document.get("title") if isinstance(document, dict) else None
        if not isinstance(title, str):
            raise NotesCurationError("OpenAI curation response does not match schema")
        try:
            blocks = parseContentBlocks(document.get("blocks"))
        except ValueError as error:
            raise NotesCurationError(
                "OpenAI curation response does not match schema"
            ) from error
        curatedDocuments.append(CuratedDocument(title=title, blocks=blocks))

    return CuratedNotes(documents=curatedDocuments)
