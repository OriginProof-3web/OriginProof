// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

import {Test} from "forge-std/Test.sol";
import {Vm} from "forge-std/Vm.sol";
import {OriginProofWalletGovernance as Governance} from "../src/OriginProofWalletGovernance.sol";
import {IOriginProofWalletRegistry as Registry} from "../src/IOriginProofWalletRegistry.sol";

contract OriginProofWalletGovernanceTest is Test {
    Governance private registry;
    address private a = vm.addr(11);
    address private b = vm.addr(12);
    address private c = vm.addr(13);
    bytes32 private constant ISSUER = keccak256("iss_synthetic_office");
    bytes32 private constant KEY = keccak256("key_synthetic_office_1");
    bytes32 private constant META = keccak256("synthetic public metadata");
    bytes32 private constant COMPROMISE = keccak256("KEY_COMPROMISE");
    uint256 private challengeCounter;

    function setUp() public {
        vm.warp(1000);
        vm.roll(10);
        registry = new Governance([a, b, c]);
    }

    function proposal(uint8 action, bytes32 keyId, uint256 signerKey)
        private
        view
        returns (Registry.GovernanceProposal memory)
    {
        return Registry.GovernanceProposal(
            action,
            ISSUER,
            keyId,
            vm.addr(signerKey),
            META,
            registry.governanceNonce(ISSUER),
            uint64(block.timestamp + 300)
        );
    }

    function proof(Registry.GovernanceProposal memory p)
        private
        returns (Registry.KeyProof memory)
    {
        return Registry.KeyProof(
            3,
            keccak256("app_synthetic"),
            p.issuerId,
            p.signer,
            keccak256(abi.encode("synthetic challenge", ++challengeCounter)),
            p.deadline
        );
    }

    function sign(Registry.KeyProof memory value, uint256 key, uint256 chain, address target)
        private
        pure
        returns (bytes memory)
    {
        bytes32 domain = keccak256(
            abi.encode(
                keccak256(
                    "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
                ),
                keccak256("OriginProof"),
                keccak256("1"),
                chain,
                target
            )
        );
        bytes32 hash = keccak256(
            abi.encode(
                keccak256(
                    "KeyProof(uint8 action,bytes32 applicationId,bytes32 issuerId,address signer,bytes32 challengeNonce,uint64 deadline)"
                ),
                value
            )
        );
        (uint8 v, bytes32 r, bytes32 s) =
            vm.sign(key, keccak256(abi.encodePacked(hex"1901", domain, hash)));
        return abi.encodePacked(r, s, v);
    }

    function prepare(Registry.GovernanceProposal memory p, uint256 key) private returns (bytes32) {
        Registry.KeyProof memory value;
        bytes memory signature;
        if (p.action != 3) {
            value = proof(p);
            signature = sign(value, key, block.chainid, address(registry));
        }
        vm.prank(a);
        return registry.propose(p, value, signature);
    }

    function execute(Registry.GovernanceProposal memory p, uint256 key)
        private
        returns (bytes32 id)
    {
        id = prepare(p, key);
        vm.prank(a);
        registry.approve(id);
        vm.prank(b);
        registry.approve(id);
    }

    function registerIssuer() private {
        execute(proposal(1, KEY, 101), 101);
    }

    function assertIssuer(uint8 expected, bytes32 expectedKey, uint256 signerKey) private view {
        (uint8 state, bytes32 keyId, address signer, bytes32 metadata) = registry.getIssuer(ISSUER);
        assertEq(state, expected);
        assertEq(keyId, expectedKey);
        assertEq(signer, vm.addr(signerKey));
        assertEq(metadata, META);
    }

    function testConstructorRejectsZeroAndDuplicateApprovers() public {
        for (uint256 i; i < 3; ++i) {
            address[3] memory approvers = [a, b, c];
            approvers[i] = address(0);
            vm.expectRevert(Governance.InvalidApprovers.selector);
            new Governance(approvers);
        }
        vm.expectRevert(Governance.InvalidApprovers.selector);
        new Governance([a, a, c]);
        vm.expectRevert(Governance.InvalidApprovers.selector);
        new Governance([a, b, a]);
        vm.expectRevert(Governance.InvalidApprovers.selector);
        new Governance([a, b, b]);
    }

    function testCreationIsNotApprovalAndSecondApprovalExecutes() public {
        Registry.GovernanceProposal memory p = proposal(1, KEY, 101);
        bytes32 id = prepare(p, 101);
        assertEq(id, keccak256(abi.encode(block.chainid, address(registry), p)));
        (, uint8 approvals, bool executed) = registry.getProposal(id);
        assertEq(approvals, 0);
        assertFalse(executed);
        vm.prank(a);
        registry.approve(id);
        (, approvals, executed) = registry.getProposal(id);
        assertEq(approvals, 1);
        assertFalse(executed);
        vm.expectRevert(Governance.UnknownIssuer.selector);
        registry.getIssuer(ISSUER);
        vm.prank(c);
        registry.approve(id);
        assertIssuer(1, KEY, 101);
        (, approvals, executed) = registry.getProposal(id);
        assertEq(approvals, 2);
        assertTrue(executed);
        assertEq(registry.governanceNonce(ISSUER), 1);
        Registry.IssuerKey memory key = registry.getKey(KEY);
        assertEq(key.issuerId, ISSUER);
        assertEq(key.registeredBlock, 10);
        assertEq(key.retiredBlock, 0);
        vm.prank(b);
        vm.expectRevert(Governance.ProposalAlreadyExecuted.selector);
        registry.approve(id);
    }

    function testDuplicateApprovalAndDeployerBypassFail() public {
        Registry.GovernanceProposal memory p = proposal(1, KEY, 101);
        Registry.KeyProof memory value = proof(p);
        bytes memory signature = sign(value, 101, block.chainid, address(registry));
        vm.expectRevert(Governance.Unauthorized.selector);
        registry.propose(p, value, signature);
        bytes32 id = prepare(p, 101);
        vm.expectRevert(Governance.Unauthorized.selector);
        registry.approve(id);
        vm.prank(a);
        registry.approve(id);
        vm.prank(a);
        vm.expectRevert(Governance.DuplicateApproval.selector);
        registry.approve(id);
        (, uint8 count,) = registry.getProposal(id);
        assertEq(count, 1);
    }

    function testUnknownObjectsAreNotSuccessfulDefaults() public {
        vm.expectRevert(Governance.UnknownIssuer.selector);
        registry.getIssuer(ISSUER);
        vm.expectRevert(Governance.UnknownKey.selector);
        registry.getKey(KEY);
        vm.expectRevert(Governance.UnknownProposal.selector);
        registry.getProposal(KEY);
        vm.prank(a);
        vm.expectRevert(Governance.UnknownProposal.selector);
        registry.approve(KEY);
        vm.prank(a);
        vm.expectRevert(Governance.UnknownIssuer.selector);
        registry.suspendIssuer(ISSUER, COMPROMISE);
    }

    function testProofCannotBeReusedAcrossProposalIds() public {
        Registry.GovernanceProposal memory p = proposal(1, KEY, 101);
        Registry.KeyProof memory value = proof(p);
        bytes memory signature = sign(value, 101, block.chainid, address(registry));
        vm.prank(a);
        registry.propose(p, value, signature);
        vm.prank(a);
        vm.expectRevert(Governance.ProposalAlreadyExists.selector);
        registry.propose(p, value, signature);
        p.keyId = keccak256("different key id");
        vm.prank(b);
        vm.expectRevert(Governance.ChallengeAlreadyUsed.selector);
        registry.propose(p, value, signature);
    }

    function testProofMustBindIssuerSignerActionAndChallenge() public {
        Registry.GovernanceProposal memory p = proposal(1, KEY, 101);
        for (uint256 i; i < 6; ++i) {
            Registry.KeyProof memory value = proof(p);
            if (i == 0) value.issuerId = keccak256("other issuer");
            if (i == 1) value.signer = vm.addr(202);
            if (i == 2) value.action = 1;
            if (i == 3) value.challengeNonce = bytes32(0);
            if (i == 4) value.applicationId = bytes32(0);
            bytes memory signature =
                sign(value, i == 5 ? 202 : 101, block.chainid, address(registry));
            vm.prank(a);
            vm.expectRevert(Governance.InvalidKeyProof.selector);
            registry.propose(p, value, signature);
        }
        // Failed proof checks do not consume a valid challenge.
        bytes32 id = prepare(p, 101);
        (, uint8 count,) = registry.getProposal(id);
        assertEq(count, 0);
    }

    function testProofRejectsWrongChainAndContract() public {
        Registry.GovernanceProposal memory p = proposal(1, KEY, 101);
        Registry.KeyProof memory value = proof(p);
        for (uint256 i; i < 2; ++i) {
            bytes memory signature = sign(
                value,
                101,
                i == 0 ? block.chainid + 1 : block.chainid,
                i == 1 ? address(0x1234) : address(registry)
            );
            vm.prank(a);
            vm.expectRevert(Governance.InvalidKeyProof.selector);
            registry.propose(p, value, signature);
        }
        bytes memory valid = sign(value, 101, block.chainid, address(registry));
        vm.prank(a);
        registry.propose(p, value, valid);
    }

    function testMalformedAndHighSSignaturesFail() public {
        Registry.GovernanceProposal memory p = proposal(1, KEY, 101);
        Registry.KeyProof memory value = proof(p);
        bytes memory signature = sign(value, 101, block.chainid, address(registry));
        bytes32 r;
        bytes32 s;
        assembly ("memory-safe") {
            r := mload(add(signature, 32))
            s := mload(add(signature, 64))
        }
        uint256 order = 0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141;
        bytes memory highS = abi.encodePacked(
            r, bytes32(order - uint256(s)), uint8(signature[64]) == 27 ? uint8(28) : uint8(27)
        );
        vm.prank(a);
        vm.expectRevert(Governance.InvalidKeyProof.selector);
        registry.propose(p, value, highS);
        vm.prank(a);
        vm.expectRevert(Governance.InvalidKeyProof.selector);
        registry.propose(p, value, hex"00");
        signature[64] = 0;
        vm.prank(a);
        vm.expectRevert(Governance.InvalidKeyProof.selector);
        registry.propose(p, value, signature);
    }

    function testProposalCannotOutliveKeyProof() public {
        Registry.GovernanceProposal memory p = proposal(1, KEY, 101);
        Registry.KeyProof memory value = proof(p);
        --value.deadline;
        bytes memory signature = sign(value, 101, block.chainid, address(registry));
        vm.prank(a);
        vm.expectRevert(Governance.InvalidKeyProof.selector);
        registry.propose(p, value, signature);
    }

    function testDeadlineBoundaryAndExpiredCreationFail() public {
        Registry.GovernanceProposal memory p = proposal(1, KEY, 101);
        bytes32 id = prepare(p, 101);
        vm.warp(p.deadline - 1);
        vm.prank(a);
        registry.approve(id);
        vm.warp(p.deadline);
        vm.prank(b);
        vm.expectRevert(Governance.ProposalExpired.selector);
        registry.approve(id);
        vm.prank(a);
        vm.expectRevert(Governance.ProposalExpired.selector);
        registry.propose(p, Registry.KeyProof(0, 0, 0, address(0), 0, 0), "");
        (, uint8 count, bool executed) = registry.getProposal(id);
        assertEq(count, 1);
        assertFalse(executed);
        assertEq(registry.governanceNonce(ISSUER), 0);
    }

    function testInvalidActionIdsAndNonceFail() public {
        for (uint256 i; i < 7; ++i) {
            Registry.GovernanceProposal memory p = proposal(1, KEY, 101);
            if (i == 0) p.action = 0;
            if (i == 1) p.action = 4;
            if (i == 2) p.issuerId = 0;
            if (i == 3) p.keyId = 0;
            if (i == 4) p.signer = address(0);
            if (i == 5) p.action = 2;
            if (i == 6) p.action = 3;
            vm.prank(a);
            vm.expectRevert(Governance.InvalidProposal.selector);
            registry.propose(p, Registry.KeyProof(0, 0, 0, address(0), 0, 0), "");
        }
        Registry.GovernanceProposal memory stale = proposal(1, KEY, 101);
        stale.nonce = 1;
        vm.prank(a);
        vm.expectRevert(Governance.ProposalStale.selector);
        registry.propose(stale, Registry.KeyProof(0, 0, 0, address(0), 0, 0), "");
    }

    function testCompetingRegistrationOnlyOneExecutes() public {
        bytes32 first = prepare(proposal(1, KEY, 101), 101);
        bytes32 second = prepare(proposal(1, keccak256("other key"), 202), 202);
        vm.prank(a);
        registry.approve(first);
        vm.prank(b);
        registry.approve(second);
        vm.prank(c);
        registry.approve(first);
        vm.prank(c);
        vm.expectRevert(Governance.ProposalStale.selector);
        registry.approve(second);
        assertIssuer(1, KEY, 101);
        (, uint8 count, bool executed) = registry.getProposal(second);
        assertEq(count, 1);
        assertFalse(executed);
    }

    function testRotationPreservesHistoryAndCannotReuseRetiredSigner() public {
        registerIssuer();
        vm.roll(20);
        bytes32 nextKey = keccak256("key_2");
        execute(proposal(2, nextKey, 202), 202);
        assertIssuer(1, nextKey, 202);
        Registry.IssuerKey memory old = registry.getKey(KEY);
        assertEq(old.registeredBlock, 10);
        assertEq(old.retiredBlock, 20);
        assertEq(old.compromiseBlock, 0);
        assertEq(registry.getKey(nextKey).registeredBlock, 20);
        Registry.GovernanceProposal memory reuse = proposal(2, keccak256("key_3"), 101);
        vm.prank(a);
        vm.expectRevert(Governance.InvalidProposal.selector);
        registry.propose(reuse, Registry.KeyProof(0, 0, 0, address(0), 0, 0), "");
        reuse = proposal(2, KEY, 303);
        vm.prank(a);
        vm.expectRevert(Governance.InvalidProposal.selector);
        registry.propose(reuse, Registry.KeyProof(0, 0, 0, address(0), 0, 0), "");
    }

    function testKeyIdCannotMoveToAnotherIssuer() public {
        registerIssuer();
        Registry.GovernanceProposal memory other = proposal(1, KEY, 202);
        other.issuerId = keccak256("iss_other");
        other.nonce = 0;
        vm.prank(a);
        vm.expectRevert(Governance.InvalidProposal.selector);
        registry.propose(other, Registry.KeyProof(0, 0, 0, address(0), 0, 0), "");
    }

    function testApproverAndCurrentKeyCanSuspendButOutsiderCannot() public {
        registerIssuer();
        vm.expectRevert(Governance.Unauthorized.selector);
        registry.suspendIssuer(ISSUER, keccak256("OTHER"));
        vm.prank(a);
        vm.expectRevert(Governance.InvalidReasonCode.selector);
        registry.suspendIssuer(ISSUER, keccak256("unapproved reason"));
        vm.prank(vm.addr(101));
        registry.suspendIssuer(ISSUER, keccak256("OTHER"));
        assertIssuer(2, KEY, 101);
        assertEq(registry.governanceNonce(ISSUER), 2);
        vm.prank(b);
        registry.suspendIssuer(ISSUER, keccak256("ABUSE_REPORT"));
        assertEq(registry.governanceNonce(ISSUER), 2);
    }

    function testRetiredKeyCannotSuspend() public {
        registerIssuer();
        execute(proposal(2, keccak256("next"), 202), 202);
        vm.prank(vm.addr(101));
        vm.expectRevert(Governance.Unauthorized.selector);
        registry.suspendIssuer(ISSUER, COMPROMISE);
    }

    function testSuspensionInvalidatesPendingRotation() public {
        registerIssuer();
        bytes32 pending = prepare(proposal(2, keccak256("next"), 202), 202);
        vm.prank(a);
        registry.approve(pending);
        vm.prank(b);
        registry.suspendIssuer(ISSUER, keccak256("OTHER"));
        vm.prank(c);
        vm.expectRevert(Governance.ProposalStale.selector);
        registry.approve(pending);
        assertIssuer(2, KEY, 101);
    }

    function testReactivationNeedsTwoAndExactCurrentIdentityWithZeroProof() public {
        registerIssuer();
        vm.prank(a);
        registry.suspendIssuer(ISSUER, keccak256("OTHER"));
        Registry.GovernanceProposal memory p = proposal(3, KEY, 101);
        Registry.KeyProof memory nonzero = proof(p);
        vm.prank(a);
        vm.expectRevert(Governance.InvalidKeyProof.selector);
        registry.propose(p, nonzero, "");
        vm.prank(a);
        vm.expectRevert(Governance.InvalidKeyProof.selector);
        registry.propose(p, Registry.KeyProof(0, 0, 0, address(0), 0, 0), hex"00");
        bytes32 id = prepare(p, 0);
        vm.prank(a);
        registry.approve(id);
        assertIssuer(2, KEY, 101);
        // A no-op suspension must not invalidate the recovery proposal.
        vm.prank(b);
        registry.suspendIssuer(ISSUER, keccak256("OTHER"));
        vm.prank(c);
        registry.approve(id);
        assertIssuer(1, KEY, 101);
        assertEq(registry.governanceNonce(ISSUER), 3);
    }

    function testReactivationCannotChangeKeySignerOrMetadata() public {
        registerIssuer();
        vm.prank(a);
        registry.suspendIssuer(ISSUER, keccak256("OTHER"));
        for (uint256 i; i < 3; ++i) {
            Registry.GovernanceProposal memory p = proposal(3, KEY, 101);
            if (i == 0) p.keyId = keccak256("different");
            if (i == 1) p.signer = vm.addr(202);
            if (i == 2) p.metadataHash = keccak256("changed metadata");
            vm.prank(a);
            vm.expectRevert(Governance.InvalidProposal.selector);
            registry.propose(p, Registry.KeyProof(0, 0, 0, address(0), 0, 0), "");
        }
    }

    function testCompromiseDuringSuspensionBlocksPreparedReactivation() public {
        registerIssuer();
        vm.prank(a);
        registry.suspendIssuer(ISSUER, keccak256("OTHER"));
        bytes32 id = prepare(proposal(3, KEY, 101), 0);
        vm.prank(a);
        registry.approve(id);
        vm.roll(20);
        vm.prank(b);
        registry.suspendIssuer(ISSUER, COMPROMISE);
        assertEq(registry.governanceNonce(ISSUER), 2);
        assertEq(registry.getKey(KEY).compromiseBlock, 20);
        vm.prank(c);
        vm.expectRevert(Governance.InvalidProposal.selector);
        registry.approve(id);
        assertIssuer(2, KEY, 101);
    }

    function testCompromiseRecoveryRequiresRotationThenJointReactivation() public {
        registerIssuer();
        vm.roll(20);
        vm.prank(a);
        registry.suspendIssuer(ISSUER, COMPROMISE);
        Registry.GovernanceProposal memory bad = proposal(3, KEY, 101);
        vm.prank(a);
        vm.expectRevert(Governance.InvalidProposal.selector);
        registry.propose(bad, Registry.KeyProof(0, 0, 0, address(0), 0, 0), "");
        vm.roll(30);
        bytes32 next = keccak256("next");
        execute(proposal(2, next, 202), 202);
        assertIssuer(2, next, 202);
        assertEq(registry.getKey(KEY).compromiseBlock, 20);
        assertEq(registry.getKey(KEY).retiredBlock, 30);
        execute(proposal(3, next, 202), 0);
        assertIssuer(1, next, 202);
    }

    function testApprovalEventsAllowDistinctAddressReconstruction() public {
        vm.recordLogs();
        bytes32 id = execute(proposal(1, KEY, 101), 101);
        Vm.Log[] memory logs = vm.getRecordedLogs();
        assertEq(logs.length, 4);
        assertEq(logs[0].topics[0], keccak256("ProposalCreated(bytes32,bytes32,uint8)"));
        assertEq(logs[1].topics[0], keccak256("ProposalApproved(bytes32,address,uint8)"));
        assertEq(logs[1].topics[1], id);
        assertEq(logs[1].topics[2], bytes32(uint256(uint160(a))));
        assertEq(abi.decode(logs[1].data, (uint8)), 1);
        assertEq(logs[2].topics[2], bytes32(uint256(uint160(b))));
        assertEq(abi.decode(logs[2].data, (uint8)), 2);
        assertEq(logs[3].topics[0], keccak256("ProposalExecuted(bytes32,bytes32,uint8)"));
    }

    function testNoUnimplementedPublicationFunctionReturnsSuccess() public {
        Registry.Publish memory message;
        (bool ok,) = address(registry).call(abi.encodeCall(Registry.publish, (message, bytes(""))));
        assertFalse(ok);
        Registry.Revoke memory revoke;
        (ok,) = address(registry).call(abi.encodeCall(Registry.revoke, (revoke, bytes(""))));
        assertFalse(ok);
    }

    function testSecondApprovalFailureRollsBackApprovalAndExecution() public {
        bytes32 id = prepare(proposal(1, KEY, 101), 101);
        vm.prank(a);
        registry.approve(id);
        vm.roll(0);
        vm.prank(b);
        vm.expectRevert(Governance.InvalidBlockNumber.selector);
        registry.approve(id);
        (, uint8 count, bool executed) = registry.getProposal(id);
        assertEq(count, 1);
        assertFalse(executed);
        assertEq(registry.governanceNonce(ISSUER), 0);
        vm.roll(10);
        vm.prank(b);
        registry.approve(id);
        assertIssuer(1, KEY, 101);
    }

    function testFuzzEveryDistinctPairActivates(uint8 first, uint8 second) public {
        first = uint8(bound(first, 0, 2));
        second = uint8(bound(second, 0, 2));
        vm.assume(first != second);
        address[3] memory approvers = [a, b, c];
        bytes32 id = prepare(proposal(1, KEY, 101), 101);
        vm.prank(approvers[first]);
        registry.approve(id);
        vm.prank(approvers[second]);
        registry.approve(id);
        assertIssuer(1, KEY, 101);
    }

    function testFuzzNonApproverCannotPropose(address actor) public {
        vm.assume(actor != a && actor != b && actor != c);
        Registry.GovernanceProposal memory p = proposal(1, KEY, 101);
        Registry.KeyProof memory value = proof(p);
        bytes memory signature = sign(value, 101, block.chainid, address(registry));
        vm.prank(actor);
        vm.expectRevert(Governance.Unauthorized.selector);
        registry.propose(p, value, signature);
    }
}
