"""Redacts embedded photo bytes from Langfuse trace payloads."""

import re
from typing import Any

REDACTED_IMAGE_PLACEHOLDER = "[redacted-image-data]"
BASE64_IMAGE_DATA_URL_PATTERN = re.compile(r"data:image/[^;]+;base64,[A-Za-z0-9+/=]+")


def maskImageData(*, data: Any, **_: Any) -> Any:
    """Strip base64 image payloads before Langfuse ever sees them.

    Vision extraction calls embed the photographed slide as a base64 data
    URL in the OpenAI request. NFR-04 requires photo bytes to never leave
    process memory beyond the OpenAI call itself, so this mask is applied
    to every observation sent to Langfuse, not just the ones we expect to
    contain an image.
    """

    if isinstance(data, str):
        return BASE64_IMAGE_DATA_URL_PATTERN.sub(REDACTED_IMAGE_PLACEHOLDER, data)
    if isinstance(data, dict):
        return {key: maskImageData(data=value) for key, value in data.items()}
    if isinstance(data, list):
        return [maskImageData(data=item) for item in data]
    return data
