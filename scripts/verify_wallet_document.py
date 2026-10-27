"""Verify a wallet document using local files and direct RPC, without the service API."""

import argparse
import asyncio
import base64
import json
import re
import sys
import time
from pathlib import Path

import httpx
from originproof_core.wallet_contract import (
    DocumentView,
    VerificationMaterial,
    VerificationRequest,
    WalletDomain,
)
from originproof_core.wallet_ports import WalletDocument, WalletIssuer, WalletKey
from originproof_core.wallet_signatures import keccak_bytes
from originproof_core.wallet_verification import verify_wallet_document


class SnapshotUnavailable(Exception):
    pass


async def read_registry(client, domain, message):
    request_id = 0
    missing = object()

    async def rpc(method, params, *, not_found=None):
        nonlocal request_id
        request_id += 1
        response = await client.post(
            "", json={"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        )
        response.raise_for_status()
        body = response.json()
        if (
            not isinstance(body, dict)
            or body.get("jsonrpc") != "2.0"
            or type(body.get("id")) is not int
            or body.get("id") != request_id
        ):
            raise SnapshotUnavailable
        if "error" in body:
            error = body["error"]
            if (
                "result" not in body
                and not_found is not None
                and isinstance(error, dict)
                and type(error.get("code")) is int
                and isinstance(error.get("message"), str)
                and error.get("data") == "0x" + keccak_bytes(not_found.encode())[:4].hex()
            ):
                return missing
            raise SnapshotUnavailable
        if "result" not in body:
            raise SnapshotUnavailable
        return body["result"]

    if int(await rpc("eth_chainId", []), 16) != int(domain.chain_id):
        raise SnapshotUnavailable
    block = await rpc("eth_getBlockByNumber", ["latest", False])
    tag = block["number"]
    block_hash = block["hash"]
    if not isinstance(block_hash, str) or not re.fullmatch(r"0x[0-9a-f]{64}", block_hash):
        raise SnapshotUnavailable
    code = await rpc("eth_getCode", [domain.verifying_contract, tag])
    if not isinstance(code, str) or not re.fullmatch(r"0x(?:[0-9a-fA-F]{2})+", code):
        raise SnapshotUnavailable
    position = {
        "chain_id": domain.chain_id,
        "verifying_contract": domain.verifying_contract,
        "block_number": str(int(tag, 16)),
        "block_hash": block_hash,
    }

    async def call(signature, arguments, count, *, not_found=None):
        encoded = keccak_bytes(signature.encode())[:4] + b"".join(arguments)
        raw = await rpc(
            "eth_call",
            [{"to": domain.verifying_contract, "data": "0x" + encoded.hex()}, tag],
            not_found=not_found,
        )
        if raw is missing:
            return None
        if not isinstance(raw, str) or not re.fullmatch(
            r"0x[0-9a-fA-F]{" + str(64 * count) + r"}", raw
        ):
            raise SnapshotUnavailable
        data = bytes.fromhex(raw[2:])
        return [data[i : i + 32] for i in range(0, len(data), 32)]

    def number(value, bits=256):
        result = int.from_bytes(value)
        if result >= 2**bits:
            raise SnapshotUnavailable
        return result

    def address(value):
        if value[:12] != b"\x00" * 12:
            raise SnapshotUnavailable
        return "0x" + value[12:].hex()

    def hashed(value):
        return "0x" + value.hex()

    did = bytes.fromhex(message.document_id[2:])
    values = await call(
        "getDocument(bytes32,uint64)",
        [did, message.version.to_bytes(32)],
        12,
        not_found="UnknownDocument()",
    )
    chain, issuer, key = None, None, None
    if values is not None and values[0] != bytes(32):
        latest = number((await call("latestVersion(bytes32)", [did], 1))[0], 64)
        document = DocumentView(
            document_id=message.document_id,
            issuer_id=hashed(values[0]),
            doc_key=hashed(values[1]),
            version=number(values[2], 64),
            key_id=hashed(values[3]),
            original_hash=hashed(values[4]),
            protected_hash=hashed(values[5]),
            content_schema=hashed(values[6]),
            issued_at=number(values[7], 64),
            expires_at=number(values[8], 64),
            state={1: "ACTIVE", 2: "REVOKED", 3: "SUPERSEDED"}[number(values[11], 8)],
            latest_version=latest,
            warnings=[],
            original_available=False,
        )
        chain = WalletDocument(
            **position,
            document=document,
            published_at=number(values[9], 64),
            published_block=str(number(values[10], 64)),
        )
        if chain.published_at > int(block["timestamp"], 16):
            raise SnapshotUnavailable
        iid = bytes.fromhex(document.issuer_id[2:])
        fields = await call("getIssuer(bytes32)", [iid], 4, not_found="UnknownIssuer()")
        if fields is not None and number(fields[0], 8) != 0:
            issuer = WalletIssuer(
                **position,
                issuer_id=document.issuer_id,
                state={1: "ACTIVE", 2: "SUSPENDED"}[number(fields[0], 8)],
                key_id=hashed(fields[1]),
                signer=address(fields[2]),
                metadata_hash=hashed(fields[3]),
                next_nonce=str(number((await call("nextNonce(bytes32)", [iid], 1))[0])),
                governance_nonce=str(number((await call("governanceNonce(bytes32)", [iid], 1))[0])),
            )
        fields = await call(
            "getKey(bytes32)",
            [bytes.fromhex(document.key_id[2:])],
            5,
            not_found="UnknownKey()",
        )
        if fields is not None and fields[0] != bytes(32):
            key = WalletKey(
                **position,
                key_id=document.key_id,
                issuer_id=hashed(fields[0]),
                signer=address(fields[1]),
                registered_block=str(number(fields[2], 64)),
                retired_block=str(number(fields[3], 64)) if number(fields[3], 64) else None,
                compromise_block=str(number(fields[4], 64)) if number(fields[4], 64) else None,
            )
    if (await rpc("eth_getBlockByNumber", [tag, False]))["hash"] != block_hash:
        raise SnapshotUnavailable
    return chain, issuer, key


def read_file(path):
    with Path(path).open("rb") as source:
        value = source.read(131073)
    if len(value) > 131072:
        raise ValueError("file too large")
    return value


async def verify(args, *, transport=None):
    material = VerificationMaterial.model_validate_json(read_file(args.material))
    signing, message = material.signing_request, material.signing_request.message
    if (
        signing.primary_type != "Publish"
        or signing.content is None
        or signing.original_base64 is None
    ):
        raise ValueError("publication material required")
    domain = WalletDomain(chainId=args.chain_id, verifyingContract=args.registry)
    if signing.domain != domain:
        raise ValueError("domain mismatch")
    original = read_file(args.original) if args.original else None
    candidate = json.loads(read_file(args.candidate)) if args.candidate else None
    metadata = json.loads(read_file(args.metadata)) if args.metadata else None
    if metadata is not None and not isinstance(metadata, dict):
        raise ValueError("metadata must be an object")
    request = VerificationRequest(
        request_id="req_independent_verification",
        document_id=message.document_id,
        version=message.version,
        scope="ORIGINAL_BYTES"
        if args.original
        else ("PROTECTED_FIELDS" if args.candidate else "ID_ONLY"),
        original_ref="inp_local" if args.original else None,
        candidate=candidate,
    )
    chain, issuer, key, unavailable = None, None, None, False
    try:
        async with (
            asyncio.timeout(30),
            httpx.AsyncClient(
                base_url=args.rpc_url, timeout=5, trust_env=False, transport=transport
            ) as client,
        ):
            chain, issuer, key = await read_registry(client, domain, message)
    except (
        httpx.HTTPError,
        httpx.InvalidURL,
        SnapshotUnavailable,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError,
    ):
        unavailable = True
    return verify_wallet_document(
        request,
        domain,
        checked_at=int(time.time()),
        chain=chain,
        issuer=issuer,
        key=key,
        message=message,
        content=signing.content,
        signature=material.signature,
        original=base64.b64decode(signing.original_base64, validate=True),
        candidate_original=original,
        metadata=metadata,
        unavailable=unavailable,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--material", required=True, help="VerificationMaterial JSON export")
    parser.add_argument("--rpc-url", required=True)
    parser.add_argument("--chain-id", required=True, help="trusted decimal chain ID")
    parser.add_argument("--registry", required=True, help="trusted deployed Registry address")
    parser.add_argument(
        "--metadata", help="public issuer metadata JSON; missing data remains inconclusive"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--original", help="received original file, compared as exact bytes")
    group.add_argument("--candidate", help="received protected fields as a JSON object")
    group.add_argument("--id-only", action="store_true")
    args = parser.parse_args()
    try:
        result = asyncio.run(verify(args))
    except (OSError, ValueError, TypeError):
        print(json.dumps({"detail": "INVALID_LOCAL_VERIFICATION_INPUT"}))
        return 2
    print(result.model_dump_json())
    return (
        0
        if result.verification_status == "VERIFIED"
        else (1 if result.verification_status == "TAMPERED" else 2)
    )


if __name__ == "__main__":
    sys.exit(main())
