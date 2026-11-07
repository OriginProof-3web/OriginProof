"""The process harness must never become an unguarded operational factory."""

import json

import pytest
from wallet_api_process import process_app


@pytest.mark.parametrize(
    "flag",
    [
        "ORIGINPROOF_WALLET_LIVE",
        "ORIGINPROOF_WALLET_API_LIVE",
        "ORIGINPROOF_WALLET_API_PROCESS",
    ],
)
def test_process_factory_requires_each_explicit_opt_in(monkeypatch, flag):
    for name in (
        "ORIGINPROOF_WALLET_LIVE",
        "ORIGINPROOF_WALLET_API_LIVE",
        "ORIGINPROOF_WALLET_API_PROCESS",
    ):
        monkeypatch.setenv(name, "1")
    monkeypatch.delenv(flag)
    monkeypatch.delenv("ORIGINPROOF_WALLET_PROCESS_CONFIG", raising=False)
    with pytest.raises(RuntimeError, match="opt-in"):
        process_app()


@pytest.mark.parametrize("fault", ["remote_db", "non_disposable_db", "remote_rpc", "chain"])
def test_process_factory_rejects_non_disposable_targets(monkeypatch, tmp_path, fault):
    for flag in (
        "ORIGINPROOF_WALLET_LIVE",
        "ORIGINPROOF_WALLET_API_LIVE",
        "ORIGINPROOF_WALLET_API_PROCESS",
    ):
        monkeypatch.setenv(flag, "1")
    database = "postgresql+asyncpg://originproof@127.0.0.1:55555/originproof_wallet_api_test"
    config = {
        "settings": {"database_url": database},
        "rpc_url": "http://127.0.0.1:55556",
        "deployment": {"chain_id": 31337},
    }
    if fault == "remote_db":
        config["settings"]["database_url"] = database.replace("127.0.0.1", "db.example.invalid")
    elif fault == "non_disposable_db":
        config["settings"]["database_url"] = database.replace(
            "originproof_wallet_api_test", "live_db"
        )
    elif fault == "remote_rpc":
        config["rpc_url"] = "https://rpc.example.invalid"
    else:
        config["deployment"]["chain_id"] = 11155111
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    monkeypatch.setenv("ORIGINPROOF_WALLET_PROCESS_CONFIG", str(path))
    with pytest.raises(RuntimeError, match="only disposable"):
        process_app()
