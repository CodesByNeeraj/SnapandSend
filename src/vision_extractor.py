"""Async OpenAI vision extraction for text-bearing images."""

import base64
import json
from dataclasses import dataclass
from typing import Any
from typing import Literal

from openai import APIError

EXTRACTION_PROMPT = """
Examine this image. It may be a presentation slide, whiteboard, document page,
handwritten note, or another image containing text. Extract only visible text
and its structure. Preserve the source order and meaning. Do not infer, add,
or correct information that is not visible.

If the image is blurry, dark, textless, or otherwise unreadable, return status
`unreadable`, an empty title, and no blocks. Otherwise return status
`readable`, a concise title, and the body as an ordered list of blocks that
mirror how the content actually appears on the source: a `paragraph` block
for prose text, a `bullets` block for a list of points. Do not force prose
into bullets or bullets into a paragraph, and use multiple blocks in order
if the source mixes both.
""".strip()
EXTRACTION_ATTEMPTS = 2

PARAGRAPH_BLOCK_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"type": "string", "enum": ["paragraph"]},
        "text": {"type": "string"},
    },
    "required": ["type", "text"],
    "additionalProperties": False,
}
BULLETS_BLOCK_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"type": "string", "enum": ["bullets"]},
        "items": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["type", "items"],
    "additionalProperties": False,
}
CONTENT_BLOCK_SCHEMA = {"anyOf": [PARAGRAPH_BLOCK_SCHEMA, BULLETS_BLOCK_SCHEMA]}

EXTRACTION_RESPONSE_FORMAT = {
    "type": "json_schema",
    "name": "extracted_document",
    "description": "Structured text extracted from one uploaded image.",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["readable", "unreadable"]},
            "title": {"type": "string"},
            "blocks": {"type": "array", "items": CONTENT_BLOCK_SCHEMA},
        },
        "required": ["status", "title", "blocks"],
        "additionalProperties": False,
    },
}


class VisionExtractionError(RuntimeError):
    """Raised when extraction fails or returns invalid structured data."""


@dataclass(frozen=True)
class ContentBlock:
    """One paragraph or bullet list, in the order it appeared in the source."""

    type: Literal["paragraph", "bullets"]
    text: str | None = None
    items: list[str] | None = None


@dataclass(frozen=True)
class ExtractedDocument:
    """Text extracted from one uploaded image."""

    status: Literal["readable", "unreadable"]
    title: str
    blocks: list[ContentBlock]


class VisionExtractor:
    """Calls the injected async OpenAI client for one prepared image."""

    def __init__(self, client: Any, model: str):
        self.client = client
        self.model = model

    async def extractDocument(self, imageBytes: bytes) -> ExtractedDocument:
        """Extract typed text, retrying one failed provider call."""

        encodedImage = base64.b64encode(imageBytes).decode("ascii")
        imageUrl = f"data:image/jpeg;base64,{encodedImage}"
        request = {
            "model": self.model,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": EXTRACTION_PROMPT},
                        {"type": "input_image", "image_url": imageUrl},
                    ],
                }
            ],
            "text": {"format": EXTRACTION_RESPONSE_FORMAT},
        }

        lastError: Exception | None = None
        for _ in range(EXTRACTION_ATTEMPTS):
            try:
                response = await self.client.responses.create(**request)
                return parseExtractedDocument(response.output_text)
            except (APIError, TimeoutError) as error:
                lastError = error

        raise VisionExtractionError(
            "OpenAI extraction failed after one retry"
        ) from lastError


def parseContentBlocks(rawBlocks: Any) -> list[ContentBlock]:
    """Parse and validate a list of raw block dicts from a model response."""

    if not isinstance(rawBlocks, list):
        raise ValueError("blocks is not a list")

    blocks = []
    for rawBlock in rawBlocks:
        if not isinstance(rawBlock, dict):
            raise ValueError("block is not an object")
        blockType = rawBlock.get("type")
        if blockType == "paragraph":
            text = rawBlock.get("text")
            if not isinstance(text, str):
                raise ValueError("paragraph block is missing text")
            blocks.append(ContentBlock(type="paragraph", text=text))
        elif blockType == "bullets":
            items = rawBlock.get("items")
            validItems = isinstance(items, list) and all(
                isinstance(item, str) for item in items
            )
            if not validItems:
                raise ValueError("bullets block is missing items")
            blocks.append(ContentBlock(type="bullets", items=items))
        else:
            raise ValueError("block has an unknown type")
    return blocks


def parseExtractedDocument(outputText: str) -> ExtractedDocument:
    """Parse and validate the OpenAI structured response."""

    try:
        output = json.loads(outputText)
    except json.JSONDecodeError as error:
        raise VisionExtractionError(
            "OpenAI extraction returned invalid JSON"
        ) from error

    if not isinstance(output, dict):
        raise VisionExtractionError("OpenAI returned an invalid response")

    status = output.get("status")
    title = output.get("title")
    validStatus = status in {"readable", "unreadable"}
    if not validStatus or not isinstance(title, str):
        raise VisionExtractionError("OpenAI response does not match schema")

    try:
        blocks = parseContentBlocks(output.get("blocks"))
    except ValueError as error:
        raise VisionExtractionError("OpenAI response does not match schema") from error

    if status == "unreadable" and (title or blocks):
        raise VisionExtractionError("Unreadable image included extracted text")

    return ExtractedDocument(status=status, title=title, blocks=blocks)
