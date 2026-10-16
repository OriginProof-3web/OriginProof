from infrastructure.blockchain.models import IssuerKeyRecord, IssuerStatus, KeyStatus


def test_key_validity_includes_start_and_excludes_end() -> None:
    key = IssuerKeyRecord(
        key_id=b"k" * 32,
        issuer_id=b"i" * 32,
        signer="0x0000000000000000000000000000000000000001",
        valid_from=100,
        valid_until=200,
        status=KeyStatus.ACTIVE,
    )

    assert key.is_valid_at(100, IssuerStatus.ACTIVE)
    assert key.is_valid_at(199, IssuerStatus.ACTIVE)
    assert not key.is_valid_at(200, IssuerStatus.ACTIVE)
    assert not key.is_valid_at(150, IssuerStatus.SUSPENDED)
