"""W6-C2 real HTTP/SQLite sessions and filesystem protection; no live-chain claim."""

import os
import stat
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
import test_w2_chain_management as w2_tests
from httpx import ASGITransport, AsyncClient
from originproof_api import accounts
from originproof_api.database import AccountRow, Base, Database, SessionRow
from originproof_api.main import create_app
from originproof_api.settings import Settings
from originproof_api.signers import signer_key, verify_signer
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class LoginSession(w2_tests.AsyncSession):
    async def delete(self, row):
        self.db.delete(row)


@pytest.fixture
async def auth():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    password = "synthetic-security-password"
    with Session(engine) as db:
        db.add(
            AccountRow(
                account_id="acct_a",
                username="issuer-a",
                role="issuer",
                issuer_id="iss_a",
                password_hash=accounts.password_hash(password),
            )
        )
        db.commit()
    database = SimpleNamespace(session_factory=lambda: LoginSession(engine))
    app = create_app(database=database, settings=Settings(session_cookie_secure=True))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as client:
        yield client, engine, password
    engine.dispose()


async def sign_in(client, password):
    response = await client.post(
        "/v1/auth/login", json={"username": "issuer-a", "password": password}
    )
    assert response.status_code == 200
    return response


async def test_session_cookie_storage_expiry_and_logout_replay(auth):
    client, engine, password = auth
    login = await sign_in(client, password)
    cookie = login.headers["Set-Cookie"].lower()
    assert all(flag in cookie for flag in ("httponly", "secure", "samesite=lax", "max-age=28800"))
    assert "domain=" not in cookie
    token = client.cookies[accounts.COOKIE]
    assert (await client.get("/v1/auth/me")).json()["role"] == "issuer"
    with Session(engine) as db:
        stored = db.get(SessionRow, accounts._token_hash(token))
        assert stored.token_hash != token
        assert (
            timedelta(hours=7, minutes=59)
            < stored.expires_at - datetime.now(UTC).replace(tzinfo=None)
            <= timedelta(hours=8)
        )
        stored.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    assert (await client.get("/v1/auth/me")).status_code == 401
    login = await sign_in(client, password)
    token = client.cookies[accounts.COOKIE]
    assert (await client.post("/v1/auth/logout")).status_code == 403
    assert (
        await client.post("/v1/auth/logout", headers={"X-CSRF-Token": login.json()["csrf_token"]})
    ).status_code == 200
    with Session(engine) as db:
        assert db.get(SessionRow, accounts._token_hash(token)) is None
    replay = await client.get("/v1/auth/me", headers={"Cookie": f"{accounts.COOKIE}={token}"})
    assert replay.status_code == 401


async def test_csrf_unicode_and_stale_tokens_do_not_crash_or_bypass(auth):
    client, _, password = auth
    first = await sign_in(client, password)
    await sign_in(client, password)
    for value in (b"wrong", b"bad\xff", first.json()["csrf_token"].encode()):
        response = await client.post("/v1/auth/logout", headers=[(b"X-CSRF-Token", value)])
        assert response.status_code == 403
        assert response.json() == {"detail": "CSRF_REQUIRED"}
    assert (await client.get("/v1/auth/me")).status_code == 200


async def test_https_sets_secure_cookie_even_with_local_http_default(auth):
    client, _, password = auth
    client._transport.app.state.settings.session_cookie_secure = False
    login = await sign_in(client, password)
    assert "; secure" in login.headers["set-cookie"].lower()
    client.base_url = "http://test"
    login = await sign_in(client, password)
    assert "; secure" not in login.headers["set-cookie"].lower()


async def test_malformed_session_is_rejected_before_database_access():
    class NoDatabase:
        def session_factory(self):
            raise AssertionError("malformed cookie must not reach the database")

    app = create_app(database=NoDatabase())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for token in ("short", "x" * 5000, "." * 43):
            response = await client.get(
                "/v1/auth/me", headers={"Cookie": f"{accounts.COOKIE}={token}"}
            )
            assert response.status_code == 401


async def test_session_expiry_boundary_and_header_role_spoofing(auth, monkeypatch):
    client, engine, password = auth
    await sign_in(client, password)
    forged = {"X-Role": "operator", "X-Account-ID": "acct_operator", "X-Issuer-ID": "iss_b"}
    response = await client.get("/v1/operator/issuer-applications", headers=forged)
    assert response.status_code == 403
    boundary = datetime.now(UTC)
    token = client.cookies[accounts.COOKIE]
    with Session(engine) as db:
        db.get(SessionRow, accounts._token_hash(token)).expires_at = boundary
        db.commit()
    monkeypatch.setattr(accounts, "datetime", SimpleNamespace(now=lambda _: boundary))
    assert (await client.get("/v1/auth/me")).status_code == 401


async def test_login_uses_password_check_for_unknown_and_wrong_accounts(auth, monkeypatch):
    client, _, _ = auth
    checked = []
    original = accounts.password_matches

    def check(password, stored):
        checked.append(stored)
        return original(password, stored)

    monkeypatch.setattr(accounts, "password_matches", check)
    replies = [
        await client.post("/v1/auth/login", json={"username": name, "password": "wrong"})
        for name in ("unknown", "issuer-a")
    ]
    assert all(
        r.status_code == 401 and r.json() == {"detail": "INVALID_CREDENTIALS"} for r in replies
    )
    assert len(checked) == 2 and checked[0] == accounts._DUMMY_PASSWORD_HASH
    assert checked[1] != checked[0]


async def test_role_injection_and_validation_responses_do_not_expose_secrets(auth, caplog):
    client, engine, password = auth
    marker = "private-synthetic-input-marker"
    injected = await client.post(
        "/v1/auth/login",
        json={
            "username": "issuer-a",
            "password": marker,
            "role": "operator",
            "issuer_id": "iss_b",
        },
    )
    assert injected.status_code == 422 and marker not in injected.text
    response = await client.post(
        "/v1/auth/login", json={"username": "issuer-a", "password": marker}
    )
    assert response.status_code == 401 and marker not in response.text
    await sign_in(client, password)
    with Session(engine) as db:
        row = db.get(AccountRow, "acct_a")
        hashes = [row.password_hash, *db.scalars(select(SessionRow.token_hash))]
    me = await client.get("/v1/auth/me")
    assert me.json()["role"] == "issuer" and me.json()["issuer_id"] == "iss_a"
    assert all(value not in me.text for value in [password, marker, *hashes])
    assert all(value not in caplog.text for value in [password, marker, *hashes])


async def test_database_engine_suppresses_sensitive_bind_parameters():
    database = Database("postgresql+asyncpg://synthetic:unused@localhost/synthetic")
    engine = create_engine("sqlite://", hide_parameters=database.engine.sync_engine.hide_parameters)
    Base.metadata.create_all(engine)
    marker = "private-synthetic-sql-marker"
    with Session(engine) as db:
        db.add_all(
            [
                AccountRow(
                    account_id=identifier, username="duplicate", password_hash=marker, role="issuer"
                )
                for identifier in ("acct_first", "acct_second")
            ]
        )
        with pytest.raises(IntegrityError) as failure:
            db.commit()
        assert marker not in str(failure.value)
        assert "parameters hidden" in str(failure.value)
    engine.dispose()
    await database.dispose()


def test_signer_permissions_persistence_and_challenge(tmp_path):
    root = tmp_path / "signers"
    key = signer_key(str(root), "key_a", create=True)
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    assert stat.S_IMODE((root / "key_a").stat().st_mode) == 0o600
    assert signer_key(str(root), "key_a", create=True).to_bytes() == key.to_bytes()
    assert verify_signer(str(root), "key_a", key.public_key.to_checksum_address()) == key
    with pytest.raises(ValueError, match="challenge mismatch"):
        verify_signer(str(root), "key_a", "0x" + "00" * 20)
    for reference in ("../key_a", "key_a/../../outside", "bad"):
        with pytest.raises(ValueError):
            signer_key(str(root), reference)


def test_signer_directory_swap_keeps_original_descriptor(tmp_path, monkeypatch):
    root = tmp_path / "signers"
    original = signer_key(str(root), "key_a", create=True)
    real_open = os.open
    swapped = False

    def open_and_swap(path, flags, *args, **kwargs):
        nonlocal swapped
        fd = real_open(path, flags, *args, **kwargs)
        if path == root and not swapped:
            swapped = True
            root.rename(tmp_path / "original")
            root.mkdir(mode=0o700)
            (root / "key_a").write_bytes(b"\0" * 31 + b"\x01")
            (root / "key_a").chmod(0o600)
        return fd

    monkeypatch.setattr(os, "open", open_and_swap)
    assert signer_key(str(root), "key_a").to_bytes() == original.to_bytes()


def test_signer_directory_owner_is_checked(tmp_path, monkeypatch):
    root = tmp_path / "signers"
    signer_key(str(root), "key_a", create=True)
    uid = os.getuid()
    monkeypatch.setattr(os, "getuid", lambda: uid + 1)
    with pytest.raises(ValueError, match="owned and private"):
        signer_key(str(root), "key_a")


@pytest.mark.parametrize(
    "unsafe",
    [
        "directory_mode",
        "file_mode",
        "directory_link",
        "file_link",
        "hard_link",
        "fifo",
        "invalid_key",
    ],
)
def test_unsafe_signer_sources_are_rejected(tmp_path, unsafe):
    root = tmp_path / "signers"
    signer_key(str(root), "key_a", create=True)
    path = root / "key_a"
    if unsafe == "directory_mode":
        root.chmod(0o755)
    elif unsafe == "file_mode":
        path.chmod(0o644)
    elif unsafe == "directory_link":
        moved = tmp_path / "moved"
        root.rename(moved)
        root.symlink_to(moved, target_is_directory=True)
    elif unsafe == "file_link":
        path.rename(root / "original")
        path.symlink_to(root / "original")
    elif unsafe == "hard_link":
        os.link(path, tmp_path / "linked-secret")
    elif unsafe == "fifo":
        path.unlink()
        os.mkfifo(path, 0o600)
    else:
        path.write_bytes(b"\0" * 32)
    with pytest.raises((ValueError, OSError)):
        signer_key(str(root), "key_a", create=True)
