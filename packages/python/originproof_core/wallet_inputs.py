"""v5 user-input models added after D's evaluation freeze (document photos, Track B lookup).

Kept out of wallet_contract.py on purpose: D's frozen evaluation candidate (#100) pins that
file's sha256, and these request models do not change analysis behaviour.
"""

import unicodedata
from typing import Annotated, Literal

from pydantic import Field, field_validator

from .wallet_contract import SAFE_INTEGER, ContractModel, Hex32, RequestId, VerificationResult


class DocumentImageInputRequest(ContractModel):
    """One-page document photo (#92). The server checks MIME, signature, size and pixels."""

    kind: Literal["DOCUMENT_IMAGE"]
    image_media_type: Literal["image/png", "image/jpeg", "image/webp"]
    image_base64: Annotated[str, Field(min_length=1, max_length=7 * 1024 * 1024)]


class PaymentLookupKey(ContractModel):
    """Values a recipient can read off a payment message without a code or QR."""

    notice_type: Literal["PAYMENT_REQUEST"]
    amount_minor: Annotated[int, Field(strict=True, gt=0, le=SAFE_INTEGER)]
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
    payee_account_number: Annotated[str, Field(pattern=r"^[0-9]{6,32}$")]

    @field_validator("payee_account_number", mode="before")
    @classmethod
    def digits_only(cls, value):
        # Messages print accounts as 001-234-567890; the signed content stores digits only.
        return value.replace("-", "").replace(" ", "") if isinstance(value, str) else value


class OfficialLookupKey(ContractModel):
    notice_type: Literal["OFFICIAL_DOCUMENT"]
    document_number: Annotated[str, Field(min_length=1, max_length=120)]

    @field_validator("document_number", mode="before")
    @classmethod
    def same_normalization_as_content(cls, value):
        return unicodedata.normalize("NFC", value.strip()) if isinstance(value, str) else value


class DocumentLookupRequest(ContractModel):
    """Track B (#88): find a published record from a message that carries no document ID."""

    request_id: RequestId
    issuer_id: Hex32
    key: Annotated[PaymentLookupKey | OfficialLookupKey, Field(discriminator="notice_type")]


class DocumentLookupResult(ContractModel):
    """UNVERIFIED means no retained record matched; it never means the message is fake."""

    lookup_status: Literal["MATCHED", "UNVERIFIED", "AMBIGUOUS"]
    match_count: Annotated[int, Field(ge=0)]
    document_ids: list[Hex32] = Field(max_length=10)
    verification: VerificationResult | None = None
    reason_codes: list[str]
