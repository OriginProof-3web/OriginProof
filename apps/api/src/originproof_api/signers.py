"""Server-only synthetic signing keys, in a persistent private directory."""

import os
import re
import secrets
import stat
from pathlib import Path

from eth_keys import keys
from eth_keys.constants import SECPK1_N
from originproof_core import payload_hash


def signer_key(directory: str, reference: str, *, create: bool = False) -> keys.PrivateKey:
    if not re.fullmatch(r"key_[A-Za-z0-9_-]+", reference):
        raise ValueError("invalid key reference")
    root = Path(directory)
    if create:
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = root.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.getuid():
        raise ValueError("signer directory must be owned and private")
    path = root / reference
    if create:
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(fd, "wb") as stream:
                while True:
                    raw = secrets.token_bytes(32)
                    if 0 < int.from_bytes(raw, "big") < SECPK1_N:
                        key = keys.PrivateKey(raw)
                        break
                stream.write(key.to_bytes())
                stream.flush()
                os.fsync(stream.fileno())
            parent_fd = os.open(root, os.O_RDONLY)
            try:
                os.fsync(parent_fd)
            finally:
                os.close(parent_fd)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.getuid():
            raise ValueError("signer file must be owned and private")
        raw = stream.read(33)
    if len(raw) != 32 or not 0 < int.from_bytes(raw, "big") < SECPK1_N:
        raise ValueError("invalid signer material")
    return keys.PrivateKey(raw)


def verify_signer(directory: str, reference: str, expected_signer: str) -> keys.PrivateKey:
    key = signer_key(directory, reference)
    challenge = bytes.fromhex(
        payload_hash(
            {
                "domain": "originproof.signer.challenge.v1",
                "nonce": secrets.token_hex(32),
                "key_id": reference,
            }
        )[2:]
    )
    recovered = key.sign_msg_hash(challenge).recover_public_key_from_msg_hash(challenge)
    if recovered.to_checksum_address().lower() != expected_signer.lower():
        raise ValueError("signer challenge mismatch")
    return key
