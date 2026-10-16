from datetime import UTC

from originproof_core import CardPaymentNoticeCandidate

# Derive field names from M1's authoritative model instead of maintaining a second schema.
EXTRACTED_FIELDS = tuple(
    name
    for name in CardPaymentNoticeCandidate.model_fields
    if name not in {"confidence", "missing_fields"}
)


def validate_candidate(candidate: CardPaymentNoticeCandidate) -> CardPaymentNoticeCandidate:
    """Validate transport invariants without modifying or redefining M1's model."""
    # Invalid provider objects must not emit serializer warnings containing extracted values.
    checked = CardPaymentNoticeCandidate.model_validate(
        candidate.model_dump(warnings=False),
        strict=True,
    )
    values = checked.model_dump()
    for name in EXTRACTED_FIELDS:
        value = values[name]
        if isinstance(value, str) and not value.strip():
            raise ValueError("empty extracted field")
    if checked.approved_at is not None:
        if checked.approved_at.utcoffset() is None:
            raise ValueError("extracted datetime must have a timezone")
        values["approved_at"] = checked.approved_at.astimezone(UTC)
    missing = [name for name in EXTRACTED_FIELDS if values[name] is None]
    if len(checked.missing_fields) != len(missing) or set(checked.missing_fields) != set(missing):
        raise ValueError("missing_fields does not match null fields")
    values["missing_fields"] = missing
    return CardPaymentNoticeCandidate.model_validate(values, strict=True)
