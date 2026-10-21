#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
foundry_bin_dir="${FOUNDRY_BIN_DIR:-${XDG_CONFIG_HOME:-${HOME}}/.foundry/bin}"
"${foundry_bin_dir}/forge" build
jq '.abi' out/IssuerRegistry.sol/IssuerRegistry.json > abi/IssuerRegistry.json
jq '.abi' out/IssuerKeyRegistry.sol/IssuerKeyRegistry.json > abi/IssuerKeyRegistry.json
