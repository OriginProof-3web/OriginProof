#!/usr/bin/env bash
set -euo pipefail

contract_dir="$(cd "$(dirname "$0")/.." && pwd)"
cd "$contract_dir"
foundry_bin_dir="${FOUNDRY_BIN_DIR:-${XDG_CONFIG_HOME:-${HOME}}/.foundry/bin}"
forge_cmd="${foundry_bin_dir}/forge"
cast_cmd="${foundry_bin_dir}/cast"

: "${CHAIN_DEPLOYER_PRIVATE_KEY:?CHAIN_DEPLOYER_PRIVATE_KEY is required}"
rpc_url="${CHAIN_RPC_URL:-http://127.0.0.1:8545}"
chain_id="$("$cast_cmd" chain-id --rpc-url "$rpc_url")"

"$forge_cmd" script script/LegacyDeployLocal.s.sol:LegacyDeployLocal --rpc-url "$rpc_url" --broadcast
"$contract_dir/script/export_abi.sh"

broadcast_file="broadcast/LegacyDeployLocal.s.sol/${chain_id}/run-latest.json"
if [[ ! -f "$broadcast_file" ]]; then
  echo "missing Foundry broadcast output: $broadcast_file" >&2
  exit 1
fi

issuer_address="$(jq -r '.transactions[] | select(.contractName == "IssuerRegistry") | .contractAddress' "$broadcast_file" | head -n1)"
key_address="$(jq -r '.transactions[] | select(.contractName == "IssuerKeyRegistry") | .contractAddress' "$broadcast_file" | head -n1)"
deployment_block="$("$cast_cmd" block-number --rpc-url "$rpc_url")"
deployment_sha="$(git rev-parse HEAD 2>/dev/null || printf 'uncommitted-local-build')"
deployer_address="$("$cast_cmd" wallet address --private-key "$CHAIN_DEPLOYER_PRIVATE_KEY")"

jq -n \
  --argjson chain_id "$chain_id" \
  --argjson deployment_block "$deployment_block" \
  --arg deployment_commit_sha "$deployment_sha" \
  --arg deployer "$deployer_address" \
  --arg issuer_address "$issuer_address" \
  --arg key_address "$key_address" \
  '{
    schema_version: "1.0.0",
    chain_id: $chain_id,
    deployment_commit_sha: $deployment_commit_sha,
    deployment_block: $deployment_block,
    contracts: {
      IssuerRegistry: {
        address: $issuer_address,
        constructor_arguments: [$deployer]
      },
      IssuerKeyRegistry: {
        address: $key_address,
        constructor_arguments: [$deployer, $issuer_address]
      }
    }
  }' > "deployments/${chain_id}.json"

echo "deployment manifest: packages/contracts/deployments/${chain_id}.json"
