// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {IIssuerRegistry} from "./IIssuerRegistry.sol";
import {IssuerKeyRegistry} from "./IssuerKeyRegistry.sol";

contract ProofStatusRegistry is AccessControl {
    bytes32 public constant GATEWAY_ROLE = keccak256("GATEWAY_ROLE");

    enum ConsumeActorKind {
        ISSUER,
        RECIPIENT
    }

    struct ProofCommitment {
        bytes32 issuerId;
        bytes32 keyId;
        bytes32 signingDigest;
        bytes32 subjectBindingHash;
        uint64 issuedAt;
        uint64 expiresAt;
        bool singleUse;
        uint64 revokedAt;
        uint64 consumedAt;
    }

    error ZeroAddress();
    error InvalidCommitment();
    error InvalidProofWindow();
    error InvalidBlockTime();
    error ProofAlreadyExists();
    error ProofNotFound();
    error IssuerNotActive();
    error KeyNotActive();
    error KeyIssuerMismatch();
    error IssuedOutsideKeyWindow();
    error UnauthorizedIssuerOperator();
    error ProofAlreadyConsumed();
    error ProofIsRevoked();
    error ProofExpired();
    error ProofNotSingleUse();
    error ActorBindingMismatch();

    IIssuerRegistry public immutable issuerRegistry;
    IssuerKeyRegistry public immutable keyRegistry;
    mapping(bytes32 proofId => ProofCommitment proof) private _proofs;

    event ProofRegistered(bytes32 indexed proofId, bytes32 indexed issuerId, bytes32 indexed keyId);
    event ProofRevoked(bytes32 indexed proofId, uint64 revokedAt);
    event ProofConsumed(bytes32 indexed proofId, ConsumeActorKind actorKind, uint64 consumedAt);

    constructor(address admin, address gateway, IIssuerRegistry issuers, IssuerKeyRegistry keys) {
        if (
            admin == address(0) || gateway == address(0) || address(issuers) == address(0)
                || address(keys) == address(0)
        ) revert ZeroAddress();
        if (address(keys.issuerRegistry()) != address(issuers)) revert InvalidCommitment();
        issuerRegistry = issuers;
        keyRegistry = keys;
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(GATEWAY_ROLE, gateway);
    }

    function registerProof(
        bytes32 proofId,
        bytes32 issuerId,
        bytes32 keyId,
        bytes32 signingDigest,
        bytes32 subjectBindingHash,
        uint64 issuedAt,
        uint64 expiresAt,
        bool singleUse
    ) external {
        if (
            proofId == bytes32(0) || issuerId == bytes32(0) || keyId == bytes32(0)
                || signingDigest == bytes32(0) || subjectBindingHash == bytes32(0)
        ) {
            revert InvalidCommitment();
        }
        if (issuedAt >= expiresAt) revert InvalidProofWindow();
        if (_proofs[proofId].issuerId != bytes32(0)) revert ProofAlreadyExists();
        if (
            msg.sender != issuerRegistry.issuerAccount(issuerId)
                && !hasRole(GATEWAY_ROLE, msg.sender)
        ) {
            revert UnauthorizedIssuerOperator();
        }
        if (issuerRegistry.issuerStatus(issuerId) != IIssuerRegistry.IssuerStatus.ACTIVE) {
            revert IssuerNotActive();
        }
        if (keyRegistry.keyStatus(keyId) != IssuerKeyRegistry.KeyStatus.ACTIVE) {
            revert KeyNotActive();
        }
        IssuerKeyRegistry.IssuerKey memory key = keyRegistry.getKey(keyId);
        if (key.issuerId != issuerId) revert KeyIssuerMismatch();
        if (issuedAt < key.validFrom || issuedAt >= key.validUntil) {
            revert IssuedOutsideKeyWindow();
        }
        _proofs[proofId] = ProofCommitment(
            issuerId, keyId, signingDigest, subjectBindingHash, issuedAt, expiresAt, singleUse, 0, 0
        );
        emit ProofRegistered(proofId, issuerId, keyId);
    }

    function revokeProof(bytes32 proofId) external returns (bool changed) {
        ProofCommitment storage proof = _proofs[proofId];
        if (proof.issuerId == bytes32(0)) revert ProofNotFound();
        if (msg.sender != issuerRegistry.issuerAccount(proof.issuerId)) {
            revert UnauthorizedIssuerOperator();
        }
        if (proof.revokedAt != 0) return false;
        if (block.timestamp == 0 || block.timestamp > type(uint64).max) revert InvalidBlockTime();
        proof.revokedAt = uint64(block.timestamp);
        emit ProofRevoked(proofId, proof.revokedAt);
        return true;
    }

    function consumeProof(bytes32 proofId, ConsumeActorKind actorKind, bytes32 actorBinding)
        external
        onlyRole(GATEWAY_ROLE)
    {
        ProofCommitment storage proof = _proofs[proofId];
        if (proof.issuerId == bytes32(0)) revert ProofNotFound();
        if (
            actorBinding == bytes32(0)
                || actorBinding
                    != (actorKind == ConsumeActorKind.ISSUER
                            ? proof.issuerId
                            : proof.subjectBindingHash)
        ) revert ActorBindingMismatch();
        if (!proof.singleUse) revert ProofNotSingleUse();
        if (proof.revokedAt != 0) revert ProofIsRevoked();
        if (proof.consumedAt != 0) revert ProofAlreadyConsumed();
        if (block.timestamp < proof.issuedAt || block.timestamp >= proof.expiresAt) {
            revert ProofExpired();
        }
        if (issuerRegistry.issuerStatus(proof.issuerId) != IIssuerRegistry.IssuerStatus.ACTIVE) {
            revert IssuerNotActive();
        }
        if (keyRegistry.keyStatus(proof.keyId) != IssuerKeyRegistry.KeyStatus.ACTIVE) {
            revert KeyNotActive();
        }
        IssuerKeyRegistry.IssuerKey memory key = keyRegistry.getKey(proof.keyId);
        if (key.issuerId != proof.issuerId) revert KeyIssuerMismatch();
        if (proof.issuedAt < key.validFrom || proof.issuedAt >= key.validUntil) {
            revert IssuedOutsideKeyWindow();
        }
        if (block.timestamp == 0 || block.timestamp > type(uint64).max) revert InvalidBlockTime();
        proof.consumedAt = uint64(block.timestamp);
        emit ProofConsumed(proofId, actorKind, proof.consumedAt);
    }

    function getProof(bytes32 proofId) external view returns (ProofCommitment memory) {
        ProofCommitment memory proof = _proofs[proofId];
        if (proof.issuerId == bytes32(0)) revert ProofNotFound();
        return proof;
    }

    function proofStatus(bytes32 proofId) external view returns (uint8) {
        ProofCommitment storage proof = _proofs[proofId];
        if (proof.issuerId == bytes32(0)) return 0;
        if (proof.revokedAt != 0) return 2;
        if (proof.consumedAt != 0) return 3;
        return 1;
    }

    function isConsumable(bytes32 proofId, uint64 timestamp) external view returns (bool) {
        ProofCommitment storage proof = _proofs[proofId];
        if (
            proof.issuerId == bytes32(0) || !proof.singleUse || proof.revokedAt != 0
                || proof.consumedAt != 0 || timestamp < proof.issuedAt
                || timestamp >= proof.expiresAt
                || issuerRegistry.issuerStatus(proof.issuerId)
                    != IIssuerRegistry.IssuerStatus.ACTIVE
                || keyRegistry.keyStatus(proof.keyId) != IssuerKeyRegistry.KeyStatus.ACTIVE
        ) return false;
        IssuerKeyRegistry.IssuerKey memory key = keyRegistry.getKey(proof.keyId);
        return key.issuerId == proof.issuerId && proof.issuedAt >= key.validFrom
            && proof.issuedAt < key.validUntil;
    }
}
