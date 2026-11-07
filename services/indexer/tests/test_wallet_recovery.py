"""Recovery never sends; an empty scan is not evidence that resubmission is safe."""

import copy

import pytest
import test_wallet_reconciliation as wallet_fixtures
from infrastructure.blockchain.errors import (
    BlockchainConfigurationError,
    BlockchainDependencyError,
)
from infrastructure.blockchain.wallet_recovery import WalletRecovery
from test_wallet_chain import H1, H2, H3, SENDER, TX, block

env = wallet_fixtures.env


async def search(oracle, rpc, **kwargs):
    return await WalletRecovery(rpc).find_transaction(
        function="publish",
        arguments=oracle.intent,
        start_block=1,
        **kwargs,
    )


async def test_lost_response_without_hash_finds_original_no_resend(env):
    oracle, rpc, _ = env
    result = await search(oracle, rpc)
    assert [x["tx_hash"] for x in result["attempts"]] == [TX]
    assert result["attempts"][0]["evidence"]["receipt_status"] == 1
    assert result["checkpoint"] == (2, H2) and result["reached_snapshot"]
    assert result["observed_next_nonce"] == 2
    assert not any(method.startswith("eth_send") for method, _ in oracle.calls)


async def test_known_hash_rechecked_once_and_deduplicated(env):
    oracle, rpc, _ = env
    result = await search(oracle, rpc, known_tx_hash=TX)
    assert len(result["attempts"]) == 1
    assert not any(method.startswith("eth_send") for method, _ in oracle.calls)


async def test_bounded_page_can_resume_canonically(env):
    oracle, rpc, _ = env
    first = await search(oracle, rpc, max_blocks=1)
    assert not first["attempts"] and not first["reached_snapshot"]
    second = await WalletRecovery(rpc).find_transaction(
        function="publish",
        arguments=oracle.intent,
        start_block=first["next_block"],
        previous_checkpoint=first["checkpoint"],
    )
    assert len(second["attempts"]) == 1


async def test_checkpoint_reorg_does_not_continue(env):
    oracle, rpc, _ = env
    first = await search(oracle, rpc, max_blocks=1)
    # Deployment hash itself must fail closed, before any search continuation.
    oracle.blocks["0x1"] = block(1, H3)
    with pytest.raises(BlockchainDependencyError):
        await WalletRecovery(rpc).find_transaction(
            function="publish",
            arguments=oracle.intent,
            start_block=2,
            previous_checkpoint=first["checkpoint"],
        )


async def test_unmatched_calldata_with_consumed_nonce_stays_unresolved(env):
    oracle, rpc, _ = env
    oracle.tx["input"] = oracle.tx["input"].replace("7a" * 65, "7b" * 65)
    result = await search(oracle, rpc)
    assert not result["attempts"] and result["observed_next_nonce"] == 2
    assert "safe_to_resend" not in result


async def test_wrong_sender_not_adopted_as_own_transaction(env):
    oracle, rpc, _ = env
    result = await search(oracle, rpc, sender="0x" + "56" * 20)
    assert not result["attempts"]


async def test_failed_original_attempt_is_not_success(env):
    oracle, rpc, _ = env
    oracle.receipt["status"], oracle.receipt["logs"] = "0x0", []
    result = await search(oracle, rpc)
    assert result["attempts"][0]["evidence"]["receipt_status"] == 0


async def test_pending_known_hash_stays_unresolved(env):
    oracle, rpc, _ = env
    oracle.blocks["0x2"]["transactions"] = []
    oracle.receipt = None
    result = await search(oracle, rpc, known_tx_hash=TX)
    assert not result["attempts"]


async def test_included_transaction_with_missing_receipt_is_dependency_error(env):
    oracle, rpc, _ = env
    oracle.receipt = None
    with pytest.raises(BlockchainDependencyError, match="receipt unavailable"):
        await search(oracle, rpc)


async def test_transaction_budget_does_not_advance_progress(env):
    oracle, rpc, _ = env
    oracle.blocks["0x1"]["transactions"] = [H3, H2]
    with pytest.raises(BlockchainDependencyError, match="budget"):
        await search(oracle, rpc, max_transactions=1)


@pytest.mark.parametrize("patch", [{"blockHash": H1}, {"transactionIndex": "0x1"}, {"hash": H3}])
async def test_mixed_rpc_transaction_observation_rejected(env, patch):
    oracle, rpc, _ = env
    oracle.tx.update(patch)
    with pytest.raises(BlockchainDependencyError):
        await search(oracle, rpc)


@pytest.mark.parametrize(
    "kwargs",
    [{"max_blocks": 0}, {"max_blocks": True}, {"max_transactions": 0}, {"max_blocks": 1025}],
)
async def test_invalid_bounds_rejected_before_rpc(env, kwargs):
    oracle, rpc, _ = env
    with pytest.raises(BlockchainConfigurationError):
        await search(oracle, rpc, **kwargs)
    assert not oracle.calls


async def test_invalid_intent_rejected_before_rpc(env):
    oracle, rpc, _ = env
    oracle.intent = copy.deepcopy(oracle.intent)
    oracle.intent["message"]["nonce"] = False
    with pytest.raises(BlockchainConfigurationError):
        await search(oracle, rpc)
    assert not oracle.calls


async def test_governance_requires_expected_sender(env):
    oracle, rpc, _ = env
    with pytest.raises(BlockchainConfigurationError):
        await WalletRecovery(rpc).find_transaction(function="approve", arguments={}, start_block=1)
    assert not oracle.calls


async def test_future_range_never_claims_complete(env):
    oracle, rpc, _ = env
    result = await WalletRecovery(rpc).find_transaction(
        function="publish",
        arguments=oracle.intent,
        start_block=3,
        sender=SENDER,
    )
    assert result["scanned_to"] is None and not result["reached_snapshot"]


async def test_known_hash_cannot_appear_in_other_canonical_block(env):
    oracle, rpc, _ = env
    oracle.blocks["0x1"]["transactions"] = [TX]
    with pytest.raises(BlockchainDependencyError, match="across canonical blocks"):
        await search(oracle, rpc, known_tx_hash=TX)


@pytest.mark.parametrize("checkpoint", [("1", H1), (1, "bad"), (True, H1), (1,)])
async def test_bad_checkpoint_is_configuration_error(env, checkpoint):
    oracle, rpc, _ = env
    with pytest.raises(BlockchainConfigurationError):
        await WalletRecovery(rpc).find_transaction(
            function="publish",
            arguments=oracle.intent,
            start_block=2,
            previous_checkpoint=checkpoint,
        )
