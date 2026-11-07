// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

/// @notice v5-shared-0.1 proposed ABI. This interface is not a deployed Registry.
interface IOriginProofWalletRegistry {
    struct Publish {
        uint8 action;
        bytes32 issuerId;
        bytes32 docKey;
        bytes32 documentId;
        uint64 version;
        bytes32 keyId;
        bytes32 originalHash;
        bytes32 protectedHash;
        bytes32 contentSchema;
        bytes32 signatureSchema;
        uint8 originalHashAlgorithm;
        uint8 protectedHashAlgorithm;
        uint64 issuedAt;
        uint64 expiresAt;
        uint256 nonce;
        uint64 deadline;
    }

    struct Revoke {
        uint8 action;
        bytes32 issuerId;
        bytes32 docKey;
        bytes32 documentId;
        uint64 version;
        bytes32 keyId;
        uint256 nonce;
        uint64 deadline;
    }

    struct KeyProof {
        uint8 action;
        bytes32 applicationId;
        bytes32 issuerId;
        address signer;
        bytes32 challengeNonce;
        uint64 deadline;
    }

    struct GovernanceProposal {
        uint8 action;
        bytes32 issuerId;
        bytes32 keyId;
        address signer;
        bytes32 metadataHash;
        uint256 nonce;
        uint64 deadline;
    }

    struct DocumentVersion {
        bytes32 issuerId;
        bytes32 docKey;
        uint64 version;
        bytes32 keyId;
        bytes32 originalHash;
        bytes32 protectedHash;
        bytes32 contentSchema;
        uint64 issuedAt;
        uint64 expiresAt;
        uint64 publishedAt;
        uint64 publishedBlock;
        uint8 state; // 1 ACTIVE, 2 REVOKED, 3 SUPERSEDED; expiry is derived.
    }

    struct IssuerKey {
        bytes32 issuerId;
        address signer;
        uint64 registeredBlock;
        uint64 retiredBlock;
        uint64 compromiseBlock;
    }

    event ProposalCreated(bytes32 indexed proposalId, bytes32 indexed issuerId, uint8 action);
    event ProposalApproved(bytes32 indexed proposalId, address indexed approver, uint8 count);
    event ProposalExecuted(bytes32 indexed proposalId, bytes32 indexed issuerId, uint8 action);
    event IssuerSuspended(bytes32 indexed issuerId, address indexed actor, bytes32 reasonCode);
    event DocumentPublished(
        bytes32 indexed documentId, uint64 indexed version, bytes32 indexed issuerId
    );
    event DocumentRevoked(
        bytes32 indexed documentId, uint64 indexed version, bytes32 indexed issuerId
    );
    event DocumentSuperseded(
        bytes32 indexed documentId, uint64 indexed version, uint64 replacement
    );

    function propose(
        GovernanceProposal calldata proposal,
        KeyProof calldata proof,
        bytes calldata signature
    ) external returns (bytes32 proposalId);
    function approve(bytes32 proposalId) external;
    function suspendIssuer(bytes32 issuerId, bytes32 reasonCode) external;
    function publish(Publish calldata message, bytes calldata signature) external;
    function revoke(Revoke calldata message, bytes calldata signature) external;
    function nextNonce(bytes32 issuerId) external view returns (uint256);
    function governanceNonce(bytes32 issuerId) external view returns (uint256);
    function latestVersion(bytes32 documentId) external view returns (uint64);
    function getDocument(bytes32 documentId, uint64 version)
        external
        view
        returns (DocumentVersion memory);
    function getIssuer(bytes32 issuerId)
        external
        view
        returns (uint8 state, bytes32 keyId, address signer, bytes32 metadataHash);
    function getKey(bytes32 keyId) external view returns (IssuerKey memory);
    function getProposal(bytes32 proposalId)
        external
        view
        returns (GovernanceProposal memory proposal, uint8 approvals, bool executed);
}
