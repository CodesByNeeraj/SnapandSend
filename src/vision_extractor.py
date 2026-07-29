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
`unreadable`, an empty title, and no bullets. Otherwise return status
`readable`, a concise title, and the extracted points as ordered bullets.
""".strip()
EXTRACTION_ATTEMPTS = 2
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
            "bullets": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["status", "title", "bullets"],
        "additionalProperties": False,
    },
}


class VisionExtractionError(RuntimeError):
    """Raised when extraction fails or returns invalid structured data."""


@dataclass(frozen=True)
class ExtractedDocument:
    """Text extracted from one uploaded image."""

    status: Literal["readable", "unreadable"]
    title: str
    bullets: list[str]


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
    bullets = output.get("bullets")
    validStatus = status in {"readable", "unreadable"}
    validBullets = isinstance(bullets, list) and all(
        isinstance(bullet, str) for bullet in bullets
    )
    if not validStatus or not isinstance(title, str) or not validBullets:
        raise VisionExtractionError("OpenAI response does not match schema")
    if status == "unreadable" and (title or bullets):
        raise VisionExtractionError("Unreadable image included extracted text")

    return ExtractedDocument(status=status, title=title, bullets=bullets)
