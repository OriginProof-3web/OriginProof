// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

// Run only after B PR(#64/#68/#69/#78/#79) is merged: B's src/OriginProofWalletRegistry.sol
// (which inherits OriginProofWalletGovernance) is referenced by artifact name, not imported, so
// this file compiles before the merge and fails clearly at run time without the B artifact.
// Use script/deploy_wallet_registry.py; it writes deployments/<chainId>.wallet[.local].json.
// Signing comes from the CLI (--account/--ledger/--trezor, or --unlocked on Anvil); no keys here.

import {Script} from "forge-std/Script.sol";

contract DeployWalletRegistry is Script {
    string internal constant ARTIFACT = "OriginProofWalletRegistry.sol:OriginProofWalletRegistry";

    function run() external returns (address registry) {
        uint256 expectedChainId = vm.envUint("WALLET_DEPLOY_CHAIN_ID");
        require(expectedChainId == 31337 || expectedChainId == 11155111, "unsupported chain");
        require(block.chainid == expectedChainId, "connected chain does not match CHAIN_TARGET");
        address[3] memory approvers = [
            vm.envAddress("WALLET_APPROVER_1_ADDRESS"),
            vm.envAddress("WALLET_APPROVER_2_ADDRESS"),
            vm.envAddress("WALLET_APPROVER_3_ADDRESS")
        ];

        vm.startBroadcast();
        registry = vm.deployCode(ARTIFACT, abi.encode(approvers));
        vm.stopBroadcast();
    }
}
