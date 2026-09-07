from __future__ import annotations

import base64
import warnings
from io import BytesIO
from typing import Literal, Self

from PIL import Image
from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_IMAGE_BYTES = 5 * 1024 * 1024


class SemanticInput(BaseModel):
    """Untrusted input transport model, not an alternative domain Candidate schema."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    text: str | None = Field(default=None, min_length=1, max_length=10_000)
    image_base64: str | None = Field(default=None, max_length=7 * 1024 * 1024)
    image_media_type: Literal["image/png", "image/jpeg", "image/webp"] | None = None

    def __repr_args__(self):
        # Keep input content out of repr without Field metadata warnings in older FastAPI.
        return [("kind", self.kind), ("image_media_type", self.image_media_type)]

    @model_validator(mode="after")
    def validate_input(self) -> Self:
        if (self.text is None) == (self.image_base64 is None):
            raise ValueError("exactly one text or image input is required")
        if self.text is not None:
            if not self.text.strip() or self.image_media_type is not None:
                raise ValueError("text input must be nonblank and have no image MIME")
            return self
        if self.image_media_type is None:
            raise ValueError("image MIME is required")
        try:
            data = base64.b64decode(self.image_base64, validate=True)
        except ValueError:
            raise ValueError("invalid image encoding") from None
        if len(data) > MAX_IMAGE_BYTES:
            raise ValueError("image exceeds 5 MiB")
        signatures = {
            "image/png": data.startswith(b"\x89PNG\r\n\x1a\n"),
            "image/jpeg": data.startswith(b"\xff\xd8\xff"),
            "image/webp": data.startswith(b"RIFF") and data[8:12] == b"WEBP",
        }
        if not signatures[self.image_media_type]:
            raise ValueError("image signature and MIME differ")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(data)) as decoded:
                    expected = {"image/png": "PNG", "image/jpeg": "JPEG", "image/webp": "WEBP"}
                    if decoded.format != expected[self.image_media_type]:
                        raise ValueError("decoded format and MIME differ")
                    frames = getattr(decoded, "n_frames", 1)
                    if decoded.width * decoded.height > 12_000_000 or frames != 1:
                        raise ValueError("image must be one frame up to 12 megapixels")
                    decoded.verify()
                with Image.open(BytesIO(data)) as decoded:
                    decoded.load()
        except (OSError, SyntaxError, Image.DecompressionBombWarning, Image.DecompressionBombError):
            raise ValueError("image cannot be decoded safely") from None
        return self

    @property
    def kind(self) -> str:
        return "text" if self.text is not None else "image"
