from datetime import datetime

import pytest
from originproof_core import CardPaymentNotice, CardPaymentNoticeCandidate
from pydantic import ValidationError


def test_card_notice_uses_minor_currency_units() -> None:
    notice = CardPaymentNotice(
        issuer_name="Origin Mock Bank",
        masked_card="1234",
        amount_minor=154000,
        currency="KRW",
        merchant="ORIGIN CAFE",
        approved_at=datetime.fromisoformat("2026-09-03T03:14:00+00:00"),
        transaction_id="txn_demo_001",
    )
    assert notice.amount_minor == 154000


def test_candidate_never_contains_authenticity_status() -> None:
    with pytest.raises(ValidationError):
        CardPaymentNoticeCandidate(confidence=0.9, verification_status="VERIFIED")
