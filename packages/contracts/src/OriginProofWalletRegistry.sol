// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import {SafeCast} from "@openzeppelin/contracts/utils/math/SafeCast.sol";
import {OriginProofWalletGovernance} from "./OriginProofWalletGovernance.sol";
import {IOriginProofWalletRegistry as Registry} from "./IOriginProofWalletRegistry.sol";

/// @notice W2 governance and W3 first-version publication; version transitions/revocation are not implemented.
contract OriginProofWalletRegistry is OriginProofWalletGovernance {
    error InvalidPublication();
    error UnsupportedSchema();
    error InvalidPublicationWindow();
    error SignatureExpired();
    error IssuerNotActive();
    error KeyNotActive();
    error InvalidDocumentId();
    error VersionConflict();
    error NonceAlreadyUsed();
    error InvalidPublicationSignature();
    error UnknownDocument();

    bytes32 private constant PUBLISH_TYPEHASH = keccak256(
        "Publish(uint8 action,bytes32 issuerId,bytes32 docKey,bytes32 documentId,uint64 version,bytes32 keyId,bytes32 originalHash,bytes32 protectedHash,bytes32 contentSchema,bytes32 signatureSchema,uint8 originalHashAlgorithm,uint8 protectedHashAlgorithm,uint64 issuedAt,uint64 expiresAt,uint256 nonce,uint64 deadline)"
    );
    bytes32 private constant SIGNATURE_SCHEMA = keccak256("originproof.wallet.v1");
    bytes32 private constant PAYMENT_SCHEMA = keccak256("originproof.content.payment.v1");
    bytes32 private constant OFFICIAL_SCHEMA = keccak256("originproof.content.official.v1");
    uint64 private constant SAFE_INTEGER = 2 ** 53 - 1;

    mapping(bytes32 issuerId => uint256) private _nextNonces;
    mapping(bytes32 documentId => Registry.DocumentVersion) private _documents;

    constructor(address[3] memory approvers) OriginProofWalletGovernance(approvers) {}

    function publish(Registry.Publish calldata message, bytes calldata signature) external {
        if (
            message.action != 1 || message.originalHash == bytes32(0)
                || message.protectedHash == bytes32(0)
        ) revert InvalidPublication();
        if (
            message.signatureSchema != SIGNATURE_SCHEMA
                || (message.contentSchema != PAYMENT_SCHEMA
                    && message.contentSchema != OFFICIAL_SCHEMA)
                || message.originalHashAlgorithm != 1 || message.protectedHashAlgorithm != 1
        ) revert UnsupportedSchema();
        if (
            message.issuedAt >= message.deadline || message.deadline > message.expiresAt
                || message.expiresAt > SAFE_INTEGER
        ) revert InvalidPublicationWindow();
        if (block.timestamp >= message.deadline) revert SignatureExpired();
        Issuer memory issuer = _issuers[message.issuerId];
        if (issuer.state != 1) revert IssuerNotActive();
        Registry.IssuerKey memory key = _keys[message.keyId];
        if (
            message.keyId != issuer.keyId || key.issuerId != message.issuerId
                || key.signer != issuer.signer || key.registeredBlock == 0 || key.retiredBlock != 0
                || key.compromiseBlock != 0
        ) revert KeyNotActive();
        if (message.documentId != keccak256(abi.encode(message.issuerId, message.docKey))) {
            revert InvalidDocumentId();
        }
        if (message.nonce != _nextNonces[message.issuerId]) revert NonceAlreadyUsed();
        if (message.version != 1 || _documents[message.documentId].state != 0) {
            revert VersionConflict();
        }
        bytes32 digest = _hashTypedDataV4(keccak256(abi.encode(PUBLISH_TYPEHASH, message)));
        (address signer, ECDSA.RecoverError error,) = ECDSA.tryRecover(digest, signature);
        if (error != ECDSA.RecoverError.NoError || signer != issuer.signer) {
            revert InvalidPublicationSignature();
        }
        uint64 publishedBlock = _blockNumber();
        _documents[message.documentId] = Registry.DocumentVersion(
            message.issuerId,
            message.docKey,
            1,
            message.keyId,
            message.originalHash,
            message.protectedHash,
            message.contentSchema,
            message.issuedAt,
            message.expiresAt,
            SafeCast.toUint64(block.timestamp),
            publishedBlock,
            1
        );
        ++_nextNonces[message.issuerId];
        emit Registry.DocumentPublished(message.documentId, 1, message.issuerId);
    }

    function nextNonce(bytes32 issuerId) external view returns (uint256) {
        return _nextNonces[issuerId];
    }

    function latestVersion(bytes32 documentId) external view returns (uint64) {
        return _documents[documentId].version;
    }

    function getDocument(bytes32 documentId, uint64 version)
        external
        view
        returns (Registry.DocumentVersion memory)
    {
        Registry.DocumentVersion memory document = _documents[documentId];
        if (document.state == 0 || version != document.version) revert UnknownDocument();
        return document;
    }
}
