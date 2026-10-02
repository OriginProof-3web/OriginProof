// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

import {Test} from "forge-std/Test.sol";
import {Vm} from "forge-std/Vm.sol";
import {IssuerRegistry} from "../src/IssuerRegistry.sol";
import {IssuerKeyRegistry} from "../src/IssuerKeyRegistry.sol";
import {ProofStatusRegistry} from "../src/ProofStatusRegistry.sol";

contract ProofStatusRegistryTest is Test {
    IssuerRegistry internal issuers;
    IssuerKeyRegistry internal keys;
    ProofStatusRegistry internal proofs;
    address internal issuer = makeAddr("issuer");
    address internal gateway = makeAddr("gateway");
    address internal outsider = makeAddr("outsider");
    bytes32 internal constant ISSUER = keccak256("iss_origin_mock_bank");
    bytes32 internal constant KEY = keccak256("key_origin_mock_bank_001");
    bytes32 internal constant PROOF = keccak256("prf_synthetic");
    bytes32 internal constant DIGEST = keccak256("canonical synthetic envelope");
    bytes32 internal constant SUBJECT = keccak256("synthetic subject binding");

    function setUp() public {
        vm.warp(150);
        issuers = new IssuerRegistry(address(this));
        issuers.registerIssuer(ISSUER, issuer, keccak256("synthetic issuer"));
        keys = new IssuerKeyRegistry(address(this), issuers);
        vm.prank(issuer);
        keys.registerKey(KEY, ISSUER, makeAddr("signer"), 100, 300);
        proofs = new ProofStatusRegistry(address(this), gateway, issuers, keys);
    }

    function _register(bool singleUse) internal {
        vm.prank(gateway);
        proofs.registerProof(PROOF, ISSUER, KEY, DIGEST, SUBJECT, 120, 250, singleUse);
    }

    function testRegistrationIsImmutableAndCallerRestricted() public {
        vm.expectRevert(ProofStatusRegistry.UnauthorizedIssuerOperator.selector);
        proofs.registerProof(PROOF, ISSUER, KEY, DIGEST, SUBJECT, 120, 250, true);
        vm.prank(outsider);
        vm.expectRevert(ProofStatusRegistry.UnauthorizedIssuerOperator.selector);
        proofs.registerProof(PROOF, ISSUER, KEY, DIGEST, SUBJECT, 120, 250, true);

        _register(true);
        assertEq(proofs.proofStatus(PROOF), 1);
        assertTrue(proofs.isConsumable(PROOF, 150));
        ProofStatusRegistry.ProofCommitment memory saved = proofs.getProof(PROOF);
        assertEq(saved.signingDigest, DIGEST);
        assertEq(saved.subjectBindingHash, SUBJECT);
        vm.prank(issuer);
        vm.expectRevert(ProofStatusRegistry.ProofAlreadyExists.selector);
        proofs.registerProof(PROOF, ISSUER, KEY, keccak256("changed"), SUBJECT, 120, 250, true);
    }

    function testRegistrationRejectsInvalidTrustAndTime() public {
        vm.prank(gateway);
        vm.expectRevert(ProofStatusRegistry.InvalidCommitment.selector);
        proofs.registerProof(PROOF, ISSUER, KEY, bytes32(0), SUBJECT, 120, 250, true);
        vm.prank(gateway);
        vm.expectRevert(ProofStatusRegistry.InvalidProofWindow.selector);
        proofs.registerProof(PROOF, ISSUER, KEY, DIGEST, SUBJECT, 250, 250, true);
        vm.prank(gateway);
        vm.expectRevert(ProofStatusRegistry.IssuedOutsideKeyWindow.selector);
        proofs.registerProof(PROOF, ISSUER, KEY, DIGEST, SUBJECT, 99, 250, true);
        keys.revokeKey(KEY);
        vm.prank(gateway);
        vm.expectRevert(ProofStatusRegistry.KeyNotActive.selector);
        proofs.registerProof(PROOF, ISSUER, KEY, DIGEST, SUBJECT, 120, 250, true);
    }

    function testForeignIssuerKeyCannotBeCommitted() public {
        bytes32 otherIssuer = keccak256("iss_other_synthetic");
        issuers.registerIssuer(otherIssuer, outsider, keccak256("other"));
        vm.prank(gateway);
        vm.expectRevert(ProofStatusRegistry.KeyIssuerMismatch.selector);
        proofs.registerProof(PROOF, otherIssuer, KEY, DIGEST, SUBJECT, 120, 250, true);
        assertEq(proofs.proofStatus(PROOF), 0);
    }

    function testIssuerOnlyRevocationIsIdempotentAndKeepsConsumption() public {
        _register(true);
        vm.prank(gateway);
        proofs.consumeProof(PROOF, ProofStatusRegistry.ConsumeActorKind.RECIPIENT, SUBJECT);
        uint64 consumedAt = proofs.getProof(PROOF).consumedAt;
        vm.prank(outsider);
        vm.expectRevert(ProofStatusRegistry.UnauthorizedIssuerOperator.selector);
        proofs.revokeProof(PROOF);
        vm.prank(gateway);
        vm.expectRevert(ProofStatusRegistry.UnauthorizedIssuerOperator.selector);
        proofs.revokeProof(PROOF);
        vm.prank(issuer);
        assertTrue(proofs.revokeProof(PROOF));
        vm.recordLogs();
        vm.prank(issuer);
        assertFalse(proofs.revokeProof(PROOF));
        assertEq(vm.getRecordedLogs().length, 0);
        assertEq(proofs.proofStatus(PROOF), 2);
        assertEq(proofs.getProof(PROOF).consumedAt, consumedAt);
    }

    function testOnlyGatewayCanConsumeAndOnlyOnce() public {
        _register(true);
        vm.expectRevert();
        proofs.consumeProof(PROOF, ProofStatusRegistry.ConsumeActorKind.RECIPIENT, SUBJECT);
        vm.prank(issuer);
        vm.expectRevert();
        proofs.consumeProof(PROOF, ProofStatusRegistry.ConsumeActorKind.RECIPIENT, SUBJECT);
        vm.prank(outsider);
        vm.expectRevert();
        proofs.consumeProof(PROOF, ProofStatusRegistry.ConsumeActorKind.RECIPIENT, SUBJECT);
        vm.prank(gateway);
        vm.expectRevert(ProofStatusRegistry.ActorBindingMismatch.selector);
        proofs.consumeProof(PROOF, ProofStatusRegistry.ConsumeActorKind.RECIPIENT, ISSUER);
        vm.prank(gateway);
        proofs.consumeProof(PROOF, ProofStatusRegistry.ConsumeActorKind.ISSUER, ISSUER);
        assertEq(proofs.proofStatus(PROOF), 3);
        assertFalse(proofs.isConsumable(PROOF, 150));
        vm.prank(gateway);
        vm.expectRevert(ProofStatusRegistry.ProofAlreadyConsumed.selector);
        proofs.consumeProof(PROOF, ProofStatusRegistry.ConsumeActorKind.RECIPIENT, SUBJECT);
    }

    function testCompetingConsumesEmitOneEvent() public {
        _register(true);
        vm.recordLogs();
        vm.prank(gateway);
        proofs.consumeProof(PROOF, ProofStatusRegistry.ConsumeActorKind.RECIPIENT, SUBJECT);
        vm.prank(gateway);
        vm.expectRevert(ProofStatusRegistry.ProofAlreadyConsumed.selector);
        proofs.consumeProof(PROOF, ProofStatusRegistry.ConsumeActorKind.RECIPIENT, SUBJECT);
        Vm.Log[] memory logs = vm.getRecordedLogs();
        assertEq(logs.length, 1);
        assertEq(logs[0].topics[0], keccak256("ProofConsumed(bytes32,uint8,uint64)"));
    }

    function testCurrentIssuerKeyAndExpiryBlockConsumption() public {
        _register(true);
        vm.warp(250);
        assertFalse(proofs.isConsumable(PROOF, 250));
        vm.prank(gateway);
        vm.expectRevert(ProofStatusRegistry.ProofExpired.selector);
        proofs.consumeProof(PROOF, ProofStatusRegistry.ConsumeActorKind.RECIPIENT, SUBJECT);
        vm.warp(150);
        issuers.suspendIssuer(ISSUER);
        assertFalse(proofs.isConsumable(PROOF, 150));
        vm.prank(gateway);
        vm.expectRevert(ProofStatusRegistry.IssuerNotActive.selector);
        proofs.consumeProof(PROOF, ProofStatusRegistry.ConsumeActorKind.RECIPIENT, SUBJECT);
        issuers.reactivateIssuer(ISSUER);
        keys.revokeKey(KEY);
        vm.prank(gateway);
        vm.expectRevert(ProofStatusRegistry.KeyNotActive.selector);
        proofs.consumeProof(PROOF, ProofStatusRegistry.ConsumeActorKind.RECIPIENT, SUBJECT);
    }

    function testNonSingleUseAndRevokedAreRejected() public {
        _register(false);
        vm.prank(gateway);
        vm.expectRevert(ProofStatusRegistry.ProofNotSingleUse.selector);
        proofs.consumeProof(PROOF, ProofStatusRegistry.ConsumeActorKind.RECIPIENT, SUBJECT);
        vm.prank(issuer);
        proofs.revokeProof(PROOF);
        assertEq(proofs.proofStatus(PROOF), 2);
        assertFalse(proofs.isConsumable(PROOF, 150));
    }

    function testZeroBlockTimestampCannotMasqueradeAsUnchangedState() public {
        bytes32 earlyKey = keccak256("key_epoch_synthetic");
        vm.prank(issuer);
        keys.registerKey(earlyKey, ISSUER, makeAddr("early-signer"), 0, 300);
        vm.prank(gateway);
        proofs.registerProof(PROOF, ISSUER, earlyKey, DIGEST, SUBJECT, 0, 250, true);
        vm.warp(0);
        vm.prank(issuer);
        vm.expectRevert(ProofStatusRegistry.InvalidBlockTime.selector);
        proofs.revokeProof(PROOF);
        vm.prank(gateway);
        vm.expectRevert(ProofStatusRegistry.InvalidBlockTime.selector);
        proofs.consumeProof(PROOF, ProofStatusRegistry.ConsumeActorKind.RECIPIENT, SUBJECT);
        assertEq(proofs.proofStatus(PROOF), 1);
    }

    function testFuzzWrongRecipientBindingNeverConsumes(bytes32 binding) public {
        vm.assume(binding != SUBJECT);
        _register(true);
        vm.prank(gateway);
        vm.expectRevert(ProofStatusRegistry.ActorBindingMismatch.selector);
        proofs.consumeProof(PROOF, ProofStatusRegistry.ConsumeActorKind.RECIPIENT, binding);
        assertEq(proofs.proofStatus(PROOF), 1);
    }
}
