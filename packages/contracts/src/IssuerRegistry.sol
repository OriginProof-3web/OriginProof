// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {IIssuerRegistry} from "./IIssuerRegistry.sol";

contract IssuerRegistry is AccessControl, Pausable, IIssuerRegistry {
    bytes32 public constant ISSUER_MANAGER_ROLE = keccak256("ISSUER_MANAGER_ROLE");

    struct Issuer {
        address account;
        bytes32 metadataHash;
        IssuerStatus status;
    }

    error ZeroAddress();
    error EmptyIssuerId();
    error IssuerAlreadyExists(bytes32 issuerId);
    error IssuerNotFound(bytes32 issuerId);
    error InvalidStatusTransition(IssuerStatus current, IssuerStatus requested);

    mapping(bytes32 issuerId => Issuer issuer) private _issuers;

    event IssuerRegistered(
        bytes32 indexed issuerId, address indexed account, bytes32 indexed metadataHash
    );
    event IssuerStatusChanged(
        bytes32 indexed issuerId,
        IssuerStatus indexed previousStatus,
        IssuerStatus indexed newStatus
    );
    event IssuerAccountChanged(
        bytes32 indexed issuerId, address indexed previousAccount, address indexed newAccount
    );

    constructor(address initialAdmin) {
        if (initialAdmin == address(0)) revert ZeroAddress();
        _grantRole(DEFAULT_ADMIN_ROLE, initialAdmin);
        _grantRole(ISSUER_MANAGER_ROLE, initialAdmin);
    }

    function registerIssuer(bytes32 issuerId, address account, bytes32 metadataHash)
        external
        onlyRole(ISSUER_MANAGER_ROLE)
        whenNotPaused
    {
        if (issuerId == bytes32(0)) revert EmptyIssuerId();
        if (account == address(0)) revert ZeroAddress();
        if (_issuers[issuerId].status != IssuerStatus.NONE) revert IssuerAlreadyExists(issuerId);

        _issuers[issuerId] = Issuer(account, metadataHash, IssuerStatus.ACTIVE);
        emit IssuerRegistered(issuerId, account, metadataHash);
        emit IssuerStatusChanged(issuerId, IssuerStatus.NONE, IssuerStatus.ACTIVE);
    }

    function suspendIssuer(bytes32 issuerId) external onlyRole(ISSUER_MANAGER_ROLE) whenNotPaused {
        _setStatus(issuerId, IssuerStatus.ACTIVE, IssuerStatus.SUSPENDED);
    }

    function reactivateIssuer(bytes32 issuerId)
        external
        onlyRole(ISSUER_MANAGER_ROLE)
        whenNotPaused
    {
        _setStatus(issuerId, IssuerStatus.SUSPENDED, IssuerStatus.ACTIVE);
    }

    function revokeIssuer(bytes32 issuerId) external onlyRole(ISSUER_MANAGER_ROLE) {
        IssuerStatus current = _requireIssuer(issuerId).status;
        if (current != IssuerStatus.ACTIVE && current != IssuerStatus.SUSPENDED) {
            revert InvalidStatusTransition(current, IssuerStatus.REVOKED);
        }
        _issuers[issuerId].status = IssuerStatus.REVOKED;
        emit IssuerStatusChanged(issuerId, current, IssuerStatus.REVOKED);
    }

    function changeIssuerAccount(bytes32 issuerId, address newAccount)
        external
        onlyRole(ISSUER_MANAGER_ROLE)
        whenNotPaused
    {
        if (newAccount == address(0)) revert ZeroAddress();
        Issuer storage issuer = _requireIssuer(issuerId);
        if (issuer.status == IssuerStatus.REVOKED) {
            revert InvalidStatusTransition(IssuerStatus.REVOKED, IssuerStatus.ACTIVE);
        }
        address previous = issuer.account;
        issuer.account = newAccount;
        emit IssuerAccountChanged(issuerId, previous, newAccount);
    }

    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _pause();
    }

    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _unpause();
    }

    function issuerStatus(bytes32 issuerId) external view returns (IssuerStatus) {
        return _issuers[issuerId].status;
    }

    function issuerAccount(bytes32 issuerId) external view returns (address) {
        return _issuers[issuerId].account;
    }

    function getIssuer(bytes32 issuerId) external view returns (Issuer memory) {
        Issuer memory issuer = _issuers[issuerId];
        if (issuer.status == IssuerStatus.NONE) revert IssuerNotFound(issuerId);
        return issuer;
    }

    function _setStatus(bytes32 issuerId, IssuerStatus expected, IssuerStatus requested) private {
        Issuer storage issuer = _requireIssuer(issuerId);
        if (issuer.status != expected) revert InvalidStatusTransition(issuer.status, requested);
        issuer.status = requested;
        emit IssuerStatusChanged(issuerId, expected, requested);
    }

    function _requireIssuer(bytes32 issuerId) private view returns (Issuer storage issuer) {
        issuer = _issuers[issuerId];
        if (issuer.status == IssuerStatus.NONE) revert IssuerNotFound(issuerId);
    }
}
