from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

HASH = re.compile(r"0x[0-9a-fA-F]{64}")
ADDRESS = re.compile(r"0x[0-9a-fA-F]{40}")
SHA256 = re.compile(r"[0-9a-f]{64}")
COMMIT_SHA = re.compile(r"[0-9a-f]{40}")
DEPLOYMENT_ID = re.compile(r"dep_[0-9a-f]{64}")


def validate_address(value: object) -> str:
    if not isinstance(value, str) or not ADDRESS.fullmatch(value):
        raise ValueError("invalid address")
    if int(value, 16) == 0:
        raise ValueError("zero address")
    return value


def validate_hash(value: object) -> str:
    if not isinstance(value, str) or not HASH.fullmatch(value):
        raise ValueError("invalid hash")
    return value.lower()


@dataclass(frozen=True)
class ContractDeployment:
    address: str
    constructor_arguments: tuple[object, ...]
    abi_sha256: str


@dataclass(frozen=True)
class DeploymentManifest:
    chain_id: int
    genesis_block_hash: str
    deployment_id: str
    deployment_block: int
    deployment_block_hash: str
    source_commit_sha: str
    contracts: dict[str, ContractDeployment]
    roles: dict[str, str]

    def contract(self, name: str) -> ContractDeployment:
        try:
            return self.contracts[name]
        except KeyError:
            raise ValueError(f"missing contract: {name}") from None


def load_manifest(path: str | Path, expected_chain_id: int) -> DeploymentManifest:
    raw = json.loads(Path(path).read_text())
    chain_id = raw["chain_id"]
    deployment_block = raw["deployment_block"]
    if type(chain_id) is not int or chain_id != expected_chain_id:
        raise ValueError("wrong manifest chain")
    if type(deployment_block) is not int or deployment_block < 0:
        raise ValueError("invalid deployment block")
    deployment_id = raw["deployment_id"]
    source_commit_sha = raw["source_commit_sha"]
    if not isinstance(deployment_id, str) or not DEPLOYMENT_ID.fullmatch(deployment_id):
        raise ValueError("invalid deployment id")
    if not isinstance(source_commit_sha, str) or not COMMIT_SHA.fullmatch(source_commit_sha):
        raise ValueError("invalid source commit")

    contracts: dict[str, ContractDeployment] = {}
    for name in ("IssuerRegistry", "IssuerKeyRegistry"):
        entry = raw["contracts"][name]
        abi_sha256 = entry["abi_sha256"]
        arguments = entry["constructor_arguments"]
        if not isinstance(abi_sha256, str) or not SHA256.fullmatch(abi_sha256):
            raise ValueError("invalid ABI hash")
        if not isinstance(arguments, list):
            raise ValueError("invalid constructor arguments")
        contracts[name] = ContractDeployment(
            address=validate_address(entry["address"]),
            constructor_arguments=tuple(arguments),
            abi_sha256=abi_sha256,
        )
    if "ProofStatusRegistry" in raw["contracts"]:
        entry = raw["contracts"]["ProofStatusRegistry"]
        if not isinstance(entry.get("abi_sha256"), str) or not SHA256.fullmatch(
            entry["abi_sha256"]
        ):
            raise ValueError("invalid ProofStatusRegistry ABI hash")
        if not isinstance(entry.get("constructor_arguments"), list):
            raise ValueError("invalid ProofStatusRegistry constructor arguments")
        contracts["ProofStatusRegistry"] = ContractDeployment(
            address=validate_address(entry["address"]),
            constructor_arguments=tuple(entry["constructor_arguments"]),
            abi_sha256=entry["abi_sha256"],
        )
    if len({entry.address.lower() for entry in contracts.values()}) != len(contracts):
        raise ValueError("duplicate contract address")

    roles = raw["roles"]
    required_roles = ("registry_admin", "issuer_manager", "key_manager", "issuer_account")
    if "ProofStatusRegistry" in contracts:
        required_roles += ("gateway",)
    if not isinstance(roles, dict) or any(name not in roles for name in required_roles):
        raise ValueError("missing role addresses")
    validated_roles = {name: validate_address(roles[name]) for name in required_roles}
    if len({value.lower() for value in validated_roles.values()}) != len(validated_roles):
        raise ValueError("role addresses must be distinct")

    return DeploymentManifest(
        chain_id=chain_id,
        genesis_block_hash=validate_hash(raw["genesis_block_hash"]),
        deployment_id=deployment_id,
        deployment_block=deployment_block,
        deployment_block_hash=validate_hash(raw["deployment_block_hash"]),
        source_commit_sha=source_commit_sha,
        contracts=contracts,
        roles=validated_roles,
    )
