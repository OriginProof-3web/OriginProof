#!/usr/bin/env bash
set -euo pipefail

contract_dir="$(cd "$(dirname "$0")/.." && pwd)"
cd "$contract_dir"
foundry_bin_dir="${FOUNDRY_BIN_DIR:-${XDG_CONFIG_HOME:-${HOME}}/.foundry/bin}"
forge_cmd="${foundry_bin_dir}/forge"

install_if_missing() {
  local target="$1"
  local dependency="$2"
  if [[ ! -d "$target" ]]; then
    "$forge_cmd" install "$dependency" --no-git
  fi
}

install_if_missing "lib/openzeppelin-contracts" "OpenZeppelin/openzeppelin-contracts@v5.7.0"
install_if_missing "lib/forge-std" "foundry-rs/forge-std@v1.16.2"
