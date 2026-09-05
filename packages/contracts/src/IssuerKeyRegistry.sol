// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {IIssuerRegistry} from "./IIssuerRegistry.sol";

contract IssuerKeyRegistry is AccessControl, Pausable {
    bytes32 public constant KEY_MANAGER_ROLE = keccak256("KEY_MANAGER_ROLE");

    enum KeyStatus {
        NONE,
        ACTIVE,
        REVOKED
    }

    struct IssuerKey {
        bytes32 issuerId;
        address signer;
        uint64 validFrom;
        uint64 validUntil;
        KeyStatus status;
    }

    error ZeroAddress();
    error EmptyId();
    error IssuerNotActive(bytes32 issuerId);
    error KeyAlreadyExists(bytes32 keyId);
    error KeyNotFound(bytes32 keyId);
    error InvalidValidityWindow(uint64 validFrom, uint64 validUntil);
    error UnauthorizedIssuerOperator(address caller, bytes32 issuerId);
    error KeyAlreadyRevoked(bytes32 keyId);

    IIssuerRegistry public immutable issuerRegistry;
    mapping(bytes32 keyId => IssuerKey issuerKey) private _keys;

    event IssuerKeyRegistered(
        bytes32 indexed keyId,
        bytes32 indexed issuerId,
        address indexed signer,
        uint64 validFrom,
        uint64 validUntil
    );
    event IssuerKeyRevoked(bytes32 indexed keyId, bytes32 indexed issuerId, address indexed actor);

    constructor(address initialAdmin, IIssuerRegistry issuerRegistry_) {
        if (initialAdmin == address(0) || address(issuerRegistry_) == address(0)) {
            revert ZeroAddress();
        }
        issuerRegistry = issuerRegistry_;
        _grantRole(DEFAULT_ADMIN_ROLE, initialAdmin);
        _grantRole(KEY_MANAGER_ROLE, initialAdmin);
    }

    function registerKey(
        bytes32 keyId,
        bytes32 issuerId,
        address signer,
        uint64 validFrom,
        uint64 validUntil
    ) external whenNotPaused {
        _requireIssuerOperator(issuerId);
        if (keyId == bytes32(0) || issuerId == bytes32(0)) revert EmptyId();
        if (signer == address(0)) revert ZeroAddress();
        if (validFrom >= validUntil) revert InvalidValidityWindow(validFrom, validUntil);
        if (issuerRegistry.issuerStatus(issuerId) != IIssuerRegistry.IssuerStatus.ACTIVE) {
            revert IssuerNotActive(issuerId);
        }
        if (_keys[keyId].status != KeyStatus.NONE) revert KeyAlreadyExists(keyId);

        _keys[keyId] = IssuerKey(issuerId, signer, validFrom, validUntil, KeyStatus.ACTIVE);
        emit IssuerKeyRegistered(keyId, issuerId, signer, validFrom, validUntil);
    }

    function revokeKey(bytes32 keyId) external {
        IssuerKey storage issuerKey = _keys[keyId];
        if (issuerKey.status == KeyStatus.NONE) revert KeyNotFound(keyId);
        _requireIssuerOperator(issuerKey.issuerId);
        if (issuerKey.status == KeyStatus.REVOKED) revert KeyAlreadyRevoked(keyId);
        issuerKey.status = KeyStatus.REVOKED;
        emit IssuerKeyRevoked(keyId, issuerKey.issuerId, msg.sender);
    }

    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _pause();
    }

    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _unpause();
    }

    function getKey(bytes32 keyId) external view returns (IssuerKey memory) {
        IssuerKey memory issuerKey = _keys[keyId];
        if (issuerKey.status == KeyStatus.NONE) revert KeyNotFound(keyId);
        return issuerKey;
    }

    function keyStatus(bytes32 keyId) external view returns (KeyStatus) {
        return _keys[keyId].status;
    }

    function isKeyValid(bytes32 keyId, uint64 timestamp) external view returns (bool) {
        IssuerKey memory issuerKey = _keys[keyId];
        return issuerKey.status == KeyStatus.ACTIVE && timestamp >= issuerKey.validFrom
            && timestamp < issuerKey.validUntil
            && issuerRegistry.issuerStatus(issuerKey.issuerId)
                == IIssuerRegistry.IssuerStatus.ACTIVE;
    }

    function _requireIssuerOperator(bytes32 issuerId) private view {
        if (
            !hasRole(KEY_MANAGER_ROLE, msg.sender)
                && issuerRegistry.issuerAccount(issuerId) != msg.sender
        ) {
            revert UnauthorizedIssuerOperator(msg.sender, issuerId);
        }
    }
}

