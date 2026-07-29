"""Async OpenAI vision extraction and structured note formatting."""

import base64
from typing import Any

from openai import APIError

EXTRACTION_PROMPT = """
Extract all visible text from this slide or whiteboard image and understand its
context. Return concise Markdown with one heading followed by bullet points.
Do not invent information or add details that are not visible. If the image is
blurry, dark, or contains no readable text, return exactly:
UNPROCESSABLE_IMAGE
""".strip()
EXTRACTION_ATTEMPTS = 2


class VisionExtractionError(RuntimeError):
    """Raised after the allowed OpenAI attempts fail."""


class VisionExtractor:
    """Calls the injected async OpenAI client for one prepared image."""

    def __init__(self, client: Any, model: str):
        self.client = client
        self.model = model

    async def extractNotes(self, imageBytes: bytes) -> str | None:
        """Extract Markdown notes, retrying one failed provider call."""

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
        }

        lastError: Exception | None = None
        for _ in range(EXTRACTION_ATTEMPTS):
            try:
                response = await self.client.responses.create(**request)
                outputText = response.output_text.strip()
                if outputText == "UNPROCESSABLE_IMAGE":
                    return None
                if not isStructuredNotes(outputText):
                    raise VisionExtractionError(
                        "OpenAI extraction did not return structured Markdown"
                    )
                return outputText
            except (APIError, TimeoutError) as error:
                lastError = error

        raise VisionExtractionError(
            "OpenAI extraction failed after one retry"
        ) from lastError


def isStructuredNotes(notes: str) -> bool:
    """Return whether notes use the required heading and bullet structure."""

    lines = notes.splitlines()
    hasHeading = bool(lines) and lines[0].startswith("# ")
    hasBullet = any(line.startswith("- ") for line in lines[1:])
    return hasHeading and hasBullet
