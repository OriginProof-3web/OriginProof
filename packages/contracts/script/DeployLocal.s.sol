// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

import {Script} from "forge-std/Script.sol";
import {SafeCast} from "@openzeppelin/contracts/utils/math/SafeCast.sol";
import {IssuerRegistry} from "../src/IssuerRegistry.sol";
import {IssuerKeyRegistry} from "../src/IssuerKeyRegistry.sol";

contract DeployLocal is Script {
    function run() external {
        require(block.chainid == 31337, "local chain only");
        address admin = vm.envAddress("CHAIN_DEPLOYER_ADDRESS");
        address signer = vm.envAddress("CHAIN_MOCK_SIGNER_ADDRESS");
        uint64 start = SafeCast.toUint64(vm.envUint("CHAIN_KEY_VALID_FROM"));
        uint64 end = SafeCast.toUint64(vm.envUint("CHAIN_KEY_VALID_UNTIL"));
        vm.startBroadcast(admin);
        IssuerRegistry issuers = new IssuerRegistry(admin);
        IssuerKeyRegistry keys = new IssuerKeyRegistry(admin, issuers);
        bytes32 issuerId = keccak256("iss_origin_mock_bank");
        issuers.registerIssuer(issuerId, admin, keccak256("Origin Mock Bank"));
        keys.registerKey(keccak256("key_origin_mock_bank_001"), issuerId, signer, start, end);
        vm.stopBroadcast();
    }
}
