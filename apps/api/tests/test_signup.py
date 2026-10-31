"""Opt-in synthetic sign-up (blocks 14): reserved .invalid mail only, then normal login."""

import pytest
from httpx import ASGITransport, AsyncClient
from originproof_api.main import create_app

pytest_plugins = ("test_wallet_runtime",)

PERSONAL = {
    "kind": "personal",
    "email": "Someone@Example.invalid",
    "password": "synthetic1pass",
    "terms_accepted": True,
}


@pytest.fixture
async def client(wallet):
    def build(enabled=True):
        settings = wallet.app.state.settings.model_copy(update={"signup_enabled": enabled})
        app = create_app(database=wallet.app.state.database, settings=settings)
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    return build


async def test_personal_and_business_signup_then_login(client):
    async with client() as api:
        personal = await api.post("/v1/auth/register", json=PERSONAL)
        assert personal.status_code == 201, personal.text
        assert personal.json()["role"] == "recipient"
        assert personal.json()["username"] == "someone@example.invalid"
        assert "password" not in personal.text and "set-cookie" not in personal.headers
        business = await api.post(
            "/v1/auth/register",
            json=PERSONAL
            | {
                "kind": "business",
                "email": "staff2@bank.example.invalid",
                "issuer_id": "iss_origin_mock_bank",
            },
        )
        assert business.status_code == 201, business.text
        assert (business.json()["role"], business.json()["issuer_id"]) == (
            "issuer",
            "iss_origin_mock_bank",
        )
        login = await api.post(
            "/v1/auth/login",
            json={"username": "SOMEONE@example.invalid", "password": PERSONAL["password"]},
        )
        assert login.status_code == 200, login.text
        assert login.json()["role"] == "recipient"
        again = await api.post("/v1/auth/register", json=PERSONAL | {"password": "other1pass"})
        assert (again.status_code, again.json()["detail"]) == (409, "ACCOUNT_EXISTS")
        relogin = await api.post(
            "/v1/auth/login",
            json={"username": "someone@example.invalid", "password": PERSONAL["password"]},
        )
        assert relogin.status_code == 200  # the duplicate attempt changed nothing


@pytest.mark.parametrize(
    "change,status,code",
    [
        ({"email": "real.person@gmail.com"}, 422, "SYNTHETIC_EMAIL_REQUIRED"),
        ({"password": "onlyletters"}, 422, "WEAK_PASSWORD"),
        ({"issuer_id": "iss_origin_mock_bank"}, 422, "MALFORMED_INPUT"),
        ({"kind": "business", "issuer_id": "iss_origin_mock_bank"}, 422,
         "SYNTHETIC_ROSTER_MISMATCH"),
        ({"kind": "business", "email": "a@bank.example.invalid", "issuer_id": "iss_unknown"}, 422,
         "SYNTHETIC_ROSTER_MISMATCH"),
        ({"terms_accepted": False}, 422, None),
        ({"password": "short1"}, 422, None),
    ],
)
async def test_signup_rejections(client, change, status, code):
    async with client() as api:
        response = await api.post("/v1/auth/register", json=PERSONAL | change)
        assert response.status_code == status, response.text
        if code:
            assert response.json()["detail"] == code


async def test_signup_is_off_by_default(client):
    async with client(enabled=False) as api:
        response = await api.post("/v1/auth/register", json=PERSONAL)
        assert (response.status_code, response.json()["detail"]) == (409, "SIGNUP_DISABLED")
