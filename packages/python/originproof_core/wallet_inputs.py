"""v5 input requests beyond TEXT.

Kept out of wallet_contract.py on purpose: D's frozen evaluation candidate (#100) pins that
file's sha256, and an input-request model does not change analysis behaviour.
"""

from typing import Annotated, Literal

from pydantic import Field

from .wallet_contract import ContractModel


class DocumentImageInputRequest(ContractModel):
    """One-page document photo (#92). The server checks MIME, signature, size and pixels."""

    kind: Literal["DOCUMENT_IMAGE"]
    image_media_type: Literal["image/png", "image/jpeg", "image/webp"]
    image_base64: Annotated[str, Field(min_length=1, max_length=7 * 1024 * 1024)]
