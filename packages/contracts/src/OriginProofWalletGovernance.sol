// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import {EIP712} from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import {SafeCast} from "@openzeppelin/contracts/utils/math/SafeCast.sol";
import {IOriginProofWalletRegistry as Registry} from "./IOriginProofWalletRegistry.sol";

/// @notice W2 governance portion of the shared Registry ABI; no publication or deployment is provided.
contract OriginProofWalletGovernance is EIP712 {
    struct Issuer {
        uint8 state;
        bytes32 keyId;
        address signer;
        bytes32 metadataHash;
    }

    struct ProposalRecord {
        Registry.GovernanceProposal proposal;
        uint8 approvalMask;
        bool executed;
    }

    error InvalidApprovers();
    error Unauthorized();
    error InvalidProposal();
    error ProposalExpired();
    error ProposalStale();
    error ProposalAlreadyExists();
    error ProposalAlreadyExecuted();
    error DuplicateApproval();
    error UnknownProposal();
    error UnknownIssuer();
    error UnknownKey();
    error InvalidKeyProof();
    error ChallengeAlreadyUsed();
    error InvalidReasonCode();
    error InvalidBlockNumber();

    bytes32 private constant KEY_PROOF_TYPEHASH = keccak256(
        "KeyProof(uint8 action,bytes32 applicationId,bytes32 issuerId,address signer,bytes32 challengeNonce,uint64 deadline)"
    );
    bytes32 private constant KEY_COMPROMISE = keccak256("KEY_COMPROMISE");
    bytes32 private constant ABUSE_REPORT = keccak256("ABUSE_REPORT");
    bytes32 private constant OTHER = keccak256("OTHER");

    address private immutable _approver0;
    address private immutable _approver1;
    address private immutable _approver2;
    mapping(bytes32 issuerId => Issuer) internal _issuers;
    mapping(bytes32 keyId => Registry.IssuerKey) internal _keys;
    mapping(bytes32 issuerId => mapping(address signer => bool)) private _usedSigners;
    mapping(bytes32 issuerId => uint256) private _governanceNonces;
    mapping(bytes32 proposalId => ProposalRecord) private _proposals;
    mapping(bytes32 challengeNonce => bool) private _usedChallenges;

    constructor(address[3] memory approvers) EIP712("OriginProof", "1") {
        if (
            approvers[0] == address(0) || approvers[1] == address(0) || approvers[2] == address(0)
                || approvers[0] == approvers[1] || approvers[0] == approvers[2]
                || approvers[1] == approvers[2]
        ) revert InvalidApprovers();
        _approver0 = approvers[0];
        _approver1 = approvers[1];
        _approver2 = approvers[2];
    }

    function propose(
        Registry.GovernanceProposal calldata proposal,
        Registry.KeyProof calldata proof,
        bytes calldata signature
    ) external returns (bytes32 proposalId) {
        _approverMask(msg.sender);
        _validateProposal(proposal);
        proposalId = keccak256(abi.encode(block.chainid, address(this), proposal));
        if (_proposals[proposalId].proposal.deadline != 0) revert ProposalAlreadyExists();
        if (proposal.action == 3) {
            if (
                proof.action != 0 || proof.applicationId != bytes32(0)
                    || proof.issuerId != bytes32(0) || proof.signer != address(0)
                    || proof.challengeNonce != bytes32(0) || proof.deadline != 0
                    || signature.length != 0
            ) revert InvalidKeyProof();
        } else {
            _consumeProof(proposal, proof, signature);
        }
        _proposals[proposalId].proposal = proposal;
        emit Registry.ProposalCreated(proposalId, proposal.issuerId, proposal.action);
    }

    function approve(bytes32 proposalId) external {
        uint8 bit = _approverMask(msg.sender);
        ProposalRecord storage record = _proposals[proposalId];
        if (record.proposal.deadline == 0) revert UnknownProposal();
        if (record.executed) revert ProposalAlreadyExecuted();
        _validateProposal(record.proposal);
        if (record.approvalMask & bit != 0) revert DuplicateApproval();
        record.approvalMask |= bit;
        uint8 count = _approvalCount(record.approvalMask);
        emit Registry.ProposalApproved(proposalId, msg.sender, count);
        if (count == 2) {
            _execute(record.proposal);
            record.executed = true;
            ++_governanceNonces[record.proposal.issuerId];
            emit Registry.ProposalExecuted(
                proposalId, record.proposal.issuerId, record.proposal.action
            );
        }
    }

    function suspendIssuer(bytes32 issuerId, bytes32 reasonCode) external {
        Issuer storage issuer = _issuers[issuerId];
        if (issuer.state == 0) revert UnknownIssuer();
        if (
            msg.sender != _approver0 && msg.sender != _approver1 && msg.sender != _approver2
                && msg.sender != issuer.signer
        ) revert Unauthorized();
        if (reasonCode != KEY_COMPROMISE && reasonCode != ABUSE_REPORT && reasonCode != OTHER) {
            revert InvalidReasonCode();
        }
        bool changed;
        if (issuer.state == 1) {
            issuer.state = 2;
            ++_governanceNonces[issuerId];
            changed = true;
        }
        if (reasonCode == KEY_COMPROMISE && _keys[issuer.keyId].compromiseBlock == 0) {
            _keys[issuer.keyId].compromiseBlock = _blockNumber();
            changed = true;
        }
        if (changed) emit Registry.IssuerSuspended(issuerId, msg.sender, reasonCode);
    }

    function governanceNonce(bytes32 issuerId) external view returns (uint256) {
        return _governanceNonces[issuerId];
    }

    function getIssuer(bytes32 issuerId)
        external
        view
        returns (uint8 state, bytes32 keyId, address signer, bytes32 metadataHash)
    {
        Issuer memory issuer = _issuers[issuerId];
        if (issuer.state == 0) revert UnknownIssuer();
        return (issuer.state, issuer.keyId, issuer.signer, issuer.metadataHash);
    }

    function getKey(bytes32 keyId) external view returns (Registry.IssuerKey memory) {
        Registry.IssuerKey memory key = _keys[keyId];
        if (key.registeredBlock == 0) revert UnknownKey();
        return key;
    }

    function getProposal(bytes32 proposalId)
        external
        view
        returns (Registry.GovernanceProposal memory proposal, uint8 approvals, bool executed)
    {
        ProposalRecord storage record = _proposals[proposalId];
        if (record.proposal.deadline == 0) revert UnknownProposal();
        return (record.proposal, _approvalCount(record.approvalMask), record.executed);
    }

    function _approverMask(address actor) private view returns (uint8) {
        if (actor == _approver0) return 1;
        if (actor == _approver1) return 2;
        if (actor == _approver2) return 4;
        revert Unauthorized();
    }

    function _approvalCount(uint8 mask) private pure returns (uint8) {
        return (mask & 1) + ((mask >> 1) & 1) + ((mask >> 2) & 1);
    }

    function _validateProposal(Registry.GovernanceProposal memory proposal) private view {
        if (block.timestamp >= proposal.deadline) revert ProposalExpired();
        if (proposal.nonce != _governanceNonces[proposal.issuerId]) revert ProposalStale();
        if (
            proposal.issuerId == bytes32(0) || proposal.keyId == bytes32(0)
                || proposal.signer == address(0)
        ) revert InvalidProposal();
        Issuer memory issuer = _issuers[proposal.issuerId];
        if (proposal.action == 1 || proposal.action == 2) {
            if (
                (proposal.action == 1 && issuer.state != 0)
                    || (proposal.action == 2 && issuer.state == 0)
                    || _keys[proposal.keyId].registeredBlock != 0
                    || _usedSigners[proposal.issuerId][proposal.signer]
            ) revert InvalidProposal();
        } else if (proposal.action == 3) {
            if (
                issuer.state != 2 || proposal.keyId != issuer.keyId
                    || proposal.signer != issuer.signer
                    || proposal.metadataHash != issuer.metadataHash
                    || _keys[issuer.keyId].compromiseBlock != 0
            ) revert InvalidProposal();
        } else {
            revert InvalidProposal();
        }
    }

    function _consumeProof(
        Registry.GovernanceProposal calldata proposal,
        Registry.KeyProof calldata proof,
        bytes calldata signature
    ) private {
        if (
            proof.action != 3 || proof.applicationId == bytes32(0)
                || proof.challengeNonce == bytes32(0) || proof.issuerId != proposal.issuerId
                || proof.signer != proposal.signer || block.timestamp >= proof.deadline
                || proposal.deadline > proof.deadline
        ) revert InvalidKeyProof();
        if (_usedChallenges[proof.challengeNonce]) revert ChallengeAlreadyUsed();
        bytes32 digest = _hashTypedDataV4(keccak256(abi.encode(KEY_PROOF_TYPEHASH, proof)));
        (address signer, ECDSA.RecoverError error,) = ECDSA.tryRecover(digest, signature);
        if (error != ECDSA.RecoverError.NoError || signer != proof.signer) {
            revert InvalidKeyProof();
        }
        _usedChallenges[proof.challengeNonce] = true;
    }

    function _execute(Registry.GovernanceProposal memory proposal) private {
        Issuer storage issuer = _issuers[proposal.issuerId];
        if (proposal.action == 3) {
            issuer.state = 1;
        } else {
            uint64 currentBlock = _blockNumber();
            if (proposal.action == 1) issuer.state = 1;
            else _keys[issuer.keyId].retiredBlock = currentBlock;
            issuer.keyId = proposal.keyId;
            issuer.signer = proposal.signer;
            issuer.metadataHash = proposal.metadataHash;
            _keys[proposal.keyId] =
                Registry.IssuerKey(proposal.issuerId, proposal.signer, currentBlock, 0, 0);
            _usedSigners[proposal.issuerId][proposal.signer] = true;
        }
    }

    function _blockNumber() internal view returns (uint64) {
        if (block.number == 0) revert InvalidBlockNumber();
        return SafeCast.toUint64(block.number);
    }
}
