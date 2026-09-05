// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

import {Test} from "forge-std/Test.sol";
import {IAccessControl} from "@openzeppelin/contracts/access/IAccessControl.sol";
import {IssuerRegistry} from "../src/IssuerRegistry.sol";
import {IIssuerRegistry} from "../src/IIssuerRegistry.sol";

contract IssuerRegistryTest is Test {
    IssuerRegistry internal registry;
    address internal manager = makeAddr("manager");
    address internal outsider = makeAddr("outsider");
    address internal issuerAccount = makeAddr("mock-bank");
    bytes32 internal constant ISSUER_ID = keccak256("iss_origin_mock_bank");

    event IssuerRegistered(
        bytes32 indexed issuerId, address indexed account, bytes32 indexed metadataHash
    );

    function setUp() public {
        registry = new IssuerRegistry(address(this));
        registry.grantRole(registry.ISSUER_MANAGER_ROLE(), manager);
    }

    function testManagerRegistersIssuer() public {
        bytes32 metadataHash = keccak256("synthetic metadata");
        vm.expectEmit(true, true, true, true, address(registry));
        emit IssuerRegistered(ISSUER_ID, issuerAccount, metadataHash);
        vm.prank(manager);
        registry.registerIssuer(ISSUER_ID, issuerAccount, metadataHash);
        assertEq(
            uint8(registry.issuerStatus(ISSUER_ID)), uint8(IIssuerRegistry.IssuerStatus.ACTIVE)
        );
        assertEq(registry.issuerAccount(ISSUER_ID), issuerAccount);
    }

    function testUnauthorizedRegistrationReverts() public {
        vm.prank(outsider);
        vm.expectRevert();
        registry.registerIssuer(ISSUER_ID, issuerAccount, bytes32(0));
    }

    function testZeroAddressAndDuplicateRevert() public {
        vm.startPrank(manager);
        vm.expectRevert(IssuerRegistry.ZeroAddress.selector);
        registry.registerIssuer(ISSUER_ID, address(0), bytes32(0));
        registry.registerIssuer(ISSUER_ID, issuerAccount, bytes32(0));
        vm.expectRevert(
            abi.encodeWithSelector(IssuerRegistry.IssuerAlreadyExists.selector, ISSUER_ID)
        );
        registry.registerIssuer(ISSUER_ID, issuerAccount, bytes32(0));
        vm.stopPrank();
    }

    function testSuspendReactivateAndIrreversibleRevoke() public {
        vm.startPrank(manager);
        registry.registerIssuer(ISSUER_ID, issuerAccount, bytes32(0));
        registry.suspendIssuer(ISSUER_ID);
        assertEq(
            uint8(registry.issuerStatus(ISSUER_ID)), uint8(IIssuerRegistry.IssuerStatus.SUSPENDED)
        );
        registry.reactivateIssuer(ISSUER_ID);
        registry.revokeIssuer(ISSUER_ID);
        vm.expectRevert();
        registry.reactivateIssuer(ISSUER_ID);
        vm.stopPrank();
    }

    function testFuzzRejectsZeroIssuerId(address account) public {
        vm.assume(account != address(0));
        vm.prank(manager);
        vm.expectRevert(IssuerRegistry.EmptyIssuerId.selector);
        registry.registerIssuer(bytes32(0), account, bytes32(0));
    }
}
