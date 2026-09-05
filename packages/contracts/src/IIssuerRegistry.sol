// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

interface IIssuerRegistry {
    enum IssuerStatus {
        NONE,
        ACTIVE,
        SUSPENDED,
        REVOKED
    }

    function issuerStatus(bytes32 issuerId) external view returns (IssuerStatus);
    function issuerAccount(bytes32 issuerId) external view returns (address);
}
