// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

import {Script, console2} from "forge-std/Script.sol";
import {IssuerRegistry} from "../src/IssuerRegistry.sol";
import {IssuerKeyRegistry} from "../src/IssuerKeyRegistry.sol";

contract DeployLocal is Script {
    bytes32 internal constant MOCK_ISSUER_ID = keccak256("iss_origin_mock_bank");
    bytes32 internal constant MOCK_KEY_ID = keccak256("key_origin_mock_bank_001");

    function run() external returns (IssuerRegistry issuers, IssuerKeyRegistry keys) {
        uint256 deployerKey = vm.envUint("CHAIN_DEPLOYER_PRIVATE_KEY");
        address deployer = vm.addr(deployerKey);
        address issuerAccount = vm.envOr("CHAIN_MOCK_ISSUER_ADDRESS", deployer);
        address signer = vm.envOr("CHAIN_MOCK_SIGNER_ADDRESS", deployer);

        vm.startBroadcast(deployerKey);
        issuers = new IssuerRegistry(deployer);
        keys = new IssuerKeyRegistry(deployer, issuers);
        issuers.registerIssuer(MOCK_ISSUER_ID, issuerAccount, keccak256("Origin Mock Bank"));
        keys.registerKey(
            MOCK_KEY_ID,
            MOCK_ISSUER_ID,
            signer,
            uint64(block.timestamp),
            uint64(block.timestamp + 365 days)
        );
        vm.stopBroadcast();

        console2.log("IssuerRegistry", address(issuers));
        console2.log("IssuerKeyRegistry", address(keys));
        console2.logBytes32(MOCK_ISSUER_ID);
        console2.logBytes32(MOCK_KEY_ID);
    }
}
