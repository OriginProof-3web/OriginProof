// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

import {Test} from "forge-std/Test.sol";
import {IssuerRegistry} from "../src/IssuerRegistry.sol";
import {IssuerKeyRegistry} from "../src/IssuerKeyRegistry.sol";

contract IssuerKeyRegistryTest is Test {
    IssuerRegistry internal issuers;
    IssuerKeyRegistry internal keys;
    address internal issuerAccount = makeAddr("mock-bank");
    address internal signer = makeAddr("signer");
    address internal outsider = makeAddr("outsider");
    bytes32 internal constant ISSUER_ID = keccak256("iss_origin_mock_bank");
    bytes32 internal constant KEY_ID = keccak256("key_origin_mock_bank_001");

    event IssuerKeyRegistered(
        bytes32 indexed keyId,
        bytes32 indexed issuerId,
        address indexed signer,
        uint64 validFrom,
        uint64 validUntil
    );

    function setUp() public {
        issuers = new IssuerRegistry(address(this));
        issuers.registerIssuer(ISSUER_ID, issuerAccount, keccak256("synthetic metadata"));
        keys = new IssuerKeyRegistry(address(this), issuers);
    }

    function testIssuerRegistersAndRevokesOwnKey() public {
        vm.expectEmit(true, true, true, true, address(keys));
        emit IssuerKeyRegistered(KEY_ID, ISSUER_ID, signer, 100, 200);
        vm.prank(issuerAccount);
        keys.registerKey(KEY_ID, ISSUER_ID, signer, 100, 200);
        assertTrue(keys.isKeyValid(KEY_ID, 150));

        vm.prank(issuerAccount);
        keys.revokeKey(KEY_ID);
        assertFalse(keys.isKeyValid(KEY_ID, 150));
    }

    function testOutsiderCannotRegisterOrRevoke() public {
        vm.prank(outsider);
        vm.expectRevert();
        keys.registerKey(KEY_ID, ISSUER_ID, signer, 100, 200);

        keys.registerKey(KEY_ID, ISSUER_ID, signer, 100, 200);
        vm.prank(outsider);
        vm.expectRevert();
        keys.revokeKey(KEY_ID);
    }

    function testDuplicateZeroAddressAndInvalidWindowRevert() public {
        vm.expectRevert(IssuerKeyRegistry.ZeroAddress.selector);
        keys.registerKey(KEY_ID, ISSUER_ID, address(0), 100, 200);
        vm.expectRevert(
            abi.encodeWithSelector(
                IssuerKeyRegistry.InvalidValidityWindow.selector, uint64(200), uint64(100)
            )
        );
        keys.registerKey(KEY_ID, ISSUER_ID, signer, 200, 100);
        keys.registerKey(KEY_ID, ISSUER_ID, signer, 100, 200);
        vm.expectRevert();
        keys.registerKey(KEY_ID, ISSUER_ID, signer, 100, 200);
    }

    function testSuspendedIssuerCannotRegisterAndInvalidatesKey() public {
        keys.registerKey(KEY_ID, ISSUER_ID, signer, 100, 200);
        issuers.suspendIssuer(ISSUER_ID);
        assertFalse(keys.isKeyValid(KEY_ID, 150));
        vm.expectRevert();
        keys.registerKey(keccak256("key-2"), ISSUER_ID, signer, 100, 200);
    }

    function testValidityBoundary() public {
        keys.registerKey(KEY_ID, ISSUER_ID, signer, 100, 200);
        assertTrue(keys.isKeyValid(KEY_ID, 100));
        assertTrue(keys.isKeyValid(KEY_ID, 199));
        assertFalse(keys.isKeyValid(KEY_ID, 99));
        assertFalse(keys.isKeyValid(KEY_ID, 200));
    }
}
