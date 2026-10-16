// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

import {Test} from "forge-std/Test.sol";
import {OriginProofWalletRegistry as Wallet} from "../src/OriginProofWalletRegistry.sol";
import {OriginProofWalletGovernance as Governance} from "../src/OriginProofWalletGovernance.sol";
import {IOriginProofWalletRegistry as Registry} from "../src/IOriginProofWalletRegistry.sol";
import {WalletGolden as Golden} from "./generated/WalletGolden.sol";

contract OriginProofWalletPublicationTest is Test {
    Wallet private registry;
    address private a = vm.addr(11);
    address private b = vm.addr(12);
    bytes32 private constant PUBLISH_TYPEHASH = keccak256(
        "Publish(uint8 action,bytes32 issuerId,bytes32 docKey,bytes32 documentId,uint64 version,bytes32 keyId,bytes32 originalHash,bytes32 protectedHash,bytes32 contentSchema,bytes32 signatureSchema,uint8 originalHashAlgorithm,uint8 protectedHashAlgorithm,uint64 issuedAt,uint64 expiresAt,uint256 nonce,uint64 deadline)"
    );
    bytes32 private constant PROOF_TYPEHASH = keccak256(
        "KeyProof(uint8 action,bytes32 applicationId,bytes32 issuerId,address signer,bytes32 challengeNonce,uint64 deadline)"
    );

    event DocumentPublished(
        bytes32 indexed documentId, uint64 indexed version, bytes32 indexed issuerId
    );

    function setUp() public {
        vm.chainId(31337);
        vm.warp(1791936000);
        vm.roll(10);
        registry = new Wallet([a, b, vm.addr(13)]);
        register(Golden.proposal());
    }

    function signHash(bytes32 hash, uint256 key, uint256 chain, address target)
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
        (uint8 v, bytes32 r, bytes32 s) =
            vm.sign(key, keccak256(abi.encodePacked(hex"1901", domain, hash)));
        return abi.encodePacked(r, s, v);
    }

    function signature(Registry.Publish memory m, uint256 key) private view returns (bytes memory) {
        return
            signHash(
                keccak256(abi.encode(PUBLISH_TYPEHASH, m)), key, block.chainid, address(registry)
            );
    }

    function register(Registry.GovernanceProposal memory p) private {
        uint256 key = p.signer == vm.addr(1) ? 1 : 2;
        Registry.KeyProof memory proof = Registry.KeyProof(
            3,
            keccak256("synthetic application"),
            p.issuerId,
            p.signer,
            keccak256(abi.encode(p.issuerId, p.keyId)),
            p.deadline
        );
        bytes memory signed = signHash(
            keccak256(abi.encode(PROOF_TYPEHASH, proof)), key, block.chainid, address(registry)
        );
        vm.prank(a);
        bytes32 id = registry.propose(p, proof, signed);
        vm.prank(a);
        registry.approve(id);
        vm.prank(b);
        registry.approve(id);
    }

    function assertUnchanged(Registry.Publish memory m) private view {
        assertEq(registry.nextNonce(m.issuerId), 0);
        assertEq(registry.latestVersion(m.documentId), 0);
    }

    function testRelayerPublishesAndStoresImmutableCommitmentsAndChainPosition() public {
        Registry.Publish memory m = Golden.payment_request();
        bytes memory signed = signature(m, 1);
        vm.warp(m.issuedAt + 10);
        vm.roll(20);
        vm.expectEmit(true, true, true, true, address(registry));
        emit DocumentPublished(m.documentId, 1, m.issuerId);
        vm.prank(vm.addr(999));
        registry.publish(m, signed);
        Registry.DocumentVersion memory doc = registry.getDocument(m.documentId, 1);
        assertEq(doc.issuerId, m.issuerId);
        assertEq(doc.docKey, m.docKey);
        assertEq(doc.version, 1);
        assertEq(doc.keyId, m.keyId);
        assertEq(doc.originalHash, m.originalHash);
        assertEq(doc.protectedHash, m.protectedHash);
        assertEq(doc.contentSchema, m.contentSchema);
        assertEq(doc.issuedAt, m.issuedAt);
        assertEq(doc.expiresAt, m.expiresAt);
        assertEq(doc.publishedAt, block.timestamp);
        assertEq(doc.publishedBlock, 20);
        assertEq(doc.state, 1);
        assertEq(registry.latestVersion(m.documentId), 1);
        assertEq(registry.nextNonce(m.issuerId), 1);
        assertEq(registry.governanceNonce(m.issuerId), 1);
    }

    function testSecondDocumentConsumesNextIssuerNonce() public {
        Registry.Publish memory m = Golden.payment_request();
        registry.publish(m, signature(m, 1));
        m.docKey = keccak256("second synthetic document");
        m.documentId = keccak256(abi.encode(m.issuerId, m.docKey));
        m.nonce = 1;
        m.originalHash = sha256("second synthetic original");
        registry.publish(m, signature(m, 1));
        assertEq(registry.nextNonce(m.issuerId), 2);
        assertEq(registry.getDocument(m.documentId, 1).originalHash, m.originalHash);
    }

    function testReplayAndSameDocumentOverwriteFail() public {
        Registry.Publish memory m = Golden.payment_request();
        bytes memory signed = signature(m, 1);
        registry.publish(m, signed);
        vm.expectRevert(Wallet.VersionConflict.selector);
        registry.publish(m, signed);
        m.nonce = 1;
        m.originalHash = sha256("overwrite attempt");
        signed = signature(m, 1);
        vm.expectRevert(Wallet.VersionConflict.selector);
        registry.publish(m, signed);
        assertEq(
            registry.getDocument(m.documentId, 1).originalHash,
            Golden.payment_request().originalHash
        );
        assertEq(registry.nextNonce(m.issuerId), 1);
    }

    function testInitialVersionAndExactNonceAreRequired() public {
        Registry.Publish memory m = Golden.payment_request();
        m.version = 2;
        bytes memory signed = signature(m, 1);
        vm.expectRevert(Wallet.VersionConflict.selector);
        registry.publish(m, signed);
        m.version = 1;
        m.nonce = 1;
        signed = signature(m, 1);
        vm.expectRevert(Wallet.NonceAlreadyUsed.selector);
        registry.publish(m, signed);
        assertUnchanged(m);
    }

    function testEverySignedFieldTamperFailsWithoutStateChanges() public {
        Registry.Publish memory m = Golden.payment_request();
        bytes memory signed = signature(m, 1);
        for (uint256 i; i < 16; ++i) {
            bytes memory input = abi.encodeCall(Registry.publish, (m, signed));
            // The static Publish tuple starts immediately after the four-byte selector.
            uint256 offset = 36 + i * 32;
            assembly ("memory-safe") {
                mstore(add(input, offset), xor(mload(add(input, offset)), 1))
            }
            (bool ok,) = address(registry).call(input);
            assertFalse(ok);
            assertUnchanged(m);
        }
    }

    function testCallerCannotBypassInstitutionSignature() public {
        Registry.Publish memory m = Golden.payment_request();
        bytes memory signed = signature(m, 2);
        vm.prank(vm.addr(1));
        vm.expectRevert(Wallet.InvalidPublicationSignature.selector);
        registry.publish(m, signed);
        vm.prank(a);
        vm.expectRevert(Wallet.InvalidPublicationSignature.selector);
        registry.publish(m, signed);
        assertUnchanged(m);
    }

    function testWrongChainOrContractSignatureFails() public {
        Registry.Publish memory m = Golden.payment_request();
        bytes32 hash = keccak256(abi.encode(PUBLISH_TYPEHASH, m));
        bytes memory signed = signHash(hash, 1, block.chainid + 1, address(registry));
        vm.expectRevert(Wallet.InvalidPublicationSignature.selector);
        registry.publish(m, signed);
        signed = signHash(hash, 1, block.chainid, address(0x1234));
        vm.expectRevert(Wallet.InvalidPublicationSignature.selector);
        registry.publish(m, signed);
        assertUnchanged(m);
    }

    function testRegisteredOtherIssuerCannotTakeDocumentIdOrKey() public {
        Registry.GovernanceProposal memory p = Golden.proposal();
        p.issuerId = keccak256("iss_other_synthetic");
        p.keyId = keccak256("key_other_synthetic");
        p.signer = vm.addr(2);
        register(p);
        Registry.Publish memory m = Golden.payment_request();
        m.issuerId = p.issuerId;
        m.keyId = p.keyId;
        bytes memory signed = signature(m, 2);
        vm.expectRevert(Wallet.InvalidDocumentId.selector);
        registry.publish(m, signed);
        m.documentId = keccak256(abi.encode(m.issuerId, m.docKey));
        m.keyId = Golden.payment_request().keyId;
        signed = signature(m, 2);
        vm.expectRevert(Wallet.KeyNotActive.selector);
        registry.publish(m, signed);
        assertUnchanged(m);
        assertEq(registry.nextNonce(Golden.payment_request().issuerId), 0);
    }

    function testUnregisteredOrSuspendedIssuerCannotPublish() public {
        Registry.Publish memory m = Golden.payment_request();
        bytes memory signed = signature(m, 1);
        vm.prank(a);
        registry.suspendIssuer(m.issuerId, keccak256("OTHER"));
        vm.expectRevert(Wallet.IssuerNotActive.selector);
        registry.publish(m, signed);
        assertUnchanged(m);
        m.issuerId = keccak256("unregistered");
        signed = signature(m, 1);
        vm.expectRevert(Wallet.IssuerNotActive.selector);
        registry.publish(m, signed);
    }

    function testCompromisedKeyCannotPublishAndPastDocumentRemainsReadable() public {
        Registry.Publish memory m = Golden.payment_request();
        registry.publish(m, signature(m, 1));
        vm.prank(a);
        registry.suspendIssuer(m.issuerId, keccak256("KEY_COMPROMISE"));
        assertEq(registry.getDocument(m.documentId, 1).keyId, m.keyId);
        assertGt(registry.getKey(m.keyId).compromiseBlock, 0);
        m.docKey = keccak256("attempt after compromise");
        m.documentId = keccak256(abi.encode(m.issuerId, m.docKey));
        m.nonce = 1;
        bytes memory signed = signature(m, 1);
        vm.expectRevert(Wallet.IssuerNotActive.selector);
        registry.publish(m, signed);
        assertEq(registry.nextNonce(m.issuerId), 1);
    }

    function testNormalRotationPreservesOldDocumentAndRejectsOldKeyForNewPublication() public {
        Registry.Publish memory m = Golden.payment_request();
        registry.publish(m, signature(m, 1));
        Registry.GovernanceProposal memory p = Golden.proposal();
        p.action = 2;
        p.keyId = keccak256("rotated key");
        p.signer = vm.addr(2);
        p.nonce = registry.governanceNonce(p.issuerId);
        vm.roll(20);
        register(p);
        assertEq(registry.getDocument(m.documentId, 1).keyId, m.keyId);
        assertEq(registry.getKey(m.keyId).retiredBlock, 20);
        m.docKey = keccak256("second document");
        m.documentId = keccak256(abi.encode(m.issuerId, m.docKey));
        m.nonce = 1;
        bytes memory signed = signature(m, 1);
        vm.expectRevert(Wallet.KeyNotActive.selector);
        registry.publish(m, signed);
        m.keyId = p.keyId;
        registry.publish(m, signature(m, 2));
        assertEq(registry.nextNonce(m.issuerId), 2);
    }

    function testDeadlineBoundaryAndInvalidWindow() public {
        Registry.Publish memory m = Golden.payment_request();
        bytes memory signed = signature(m, 1);
        vm.warp(m.deadline);
        vm.expectRevert(Wallet.SignatureExpired.selector);
        registry.publish(m, signed);
        vm.warp(m.deadline - 1);
        registry.publish(m, signed);
        m.docKey = keccak256("other");
        m.documentId = keccak256(abi.encode(m.issuerId, m.docKey));
        m.nonce = 1;
        m.issuedAt = m.deadline;
        signed = signature(m, 1);
        vm.expectRevert(Wallet.InvalidPublicationWindow.selector);
        registry.publish(m, signed);
        m.issuedAt = m.deadline - 1;
        m.expiresAt = m.deadline - 1;
        signed = signature(m, 1);
        vm.expectRevert(Wallet.InvalidPublicationWindow.selector);
        registry.publish(m, signed);
        m.expiresAt = uint64(2 ** 53);
        signed = signature(m, 1);
        vm.expectRevert(Wallet.InvalidPublicationWindow.selector);
        registry.publish(m, signed);
    }

    function testUnsupportedSchemasAndAlgorithmsDoNotConsumeNonce() public {
        for (uint256 i; i < 4; ++i) {
            Registry.Publish memory m = Golden.payment_request();
            if (i == 0) m.signatureSchema = keccak256("unsupported");
            if (i == 1) m.contentSchema = keccak256("unsupported");
            if (i == 2) m.originalHashAlgorithm = 2;
            if (i == 3) m.protectedHashAlgorithm = 2;
            bytes memory signed = signature(m, 1);
            vm.expectRevert(Wallet.UnsupportedSchema.selector);
            registry.publish(m, signed);
            assertUnchanged(m);
        }
    }

    function testInvalidActionAndEmptyCommitmentsFail() public {
        for (uint256 i; i < 3; ++i) {
            Registry.Publish memory m = Golden.payment_request();
            if (i == 0) m.action = 2;
            if (i == 1) m.originalHash = 0;
            if (i == 2) m.protectedHash = 0;
            bytes memory signed = signature(m, 1);
            vm.expectRevert(Wallet.InvalidPublication.selector);
            registry.publish(m, signed);
            assertUnchanged(m);
        }
    }

    function testMalformedAndHighSSignaturesFailWithoutNonceConsumption() public {
        Registry.Publish memory m = Golden.payment_request();
        bytes memory signed = signature(m, 1);
        bytes32 r;
        bytes32 s;
        assembly ("memory-safe") {
            r := mload(add(signed, 32))
            s := mload(add(signed, 64))
        }
        uint256 order = 0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141;
        bytes memory highS = abi.encodePacked(
            r, bytes32(order - uint256(s)), uint8(signed[64]) == 27 ? uint8(28) : uint8(27)
        );
        vm.expectRevert(Wallet.InvalidPublicationSignature.selector);
        registry.publish(m, highS);
        vm.expectRevert(Wallet.InvalidPublicationSignature.selector);
        registry.publish(m, hex"00");
        signed[64] = 0;
        vm.expectRevert(Wallet.InvalidPublicationSignature.selector);
        registry.publish(m, signed);
        assertUnchanged(m);
    }

    function testStorageFailureRestoresNonceAndDocument() public {
        Registry.Publish memory m = Golden.payment_request();
        bytes memory signed = signature(m, 1);
        vm.roll(0);
        vm.expectRevert(Governance.InvalidBlockNumber.selector);
        registry.publish(m, signed);
        assertUnchanged(m);
        vm.roll(10);
        registry.publish(m, signed);
    }

    function testAbsentVersionAndInvalidRevocationAreNotSuccess() public {
        Registry.Publish memory m = Golden.payment_request();
        vm.expectRevert(Wallet.UnknownDocument.selector);
        registry.getDocument(m.documentId, 1);
        assertEq(registry.latestVersion(m.documentId), 0);
        registry.publish(m, signature(m, 1));
        vm.expectRevert(Wallet.UnknownDocument.selector);
        registry.getDocument(m.documentId, 2);
        Registry.Revoke memory revoke = Golden.revoke();
        (bool ok,) = address(registry)
            .call(abi.encodeCall(Registry.revoke, (revoke, Golden.REVOKE_SIGNATURE)));
        assertFalse(ok);
        assertEq(registry.getDocument(m.documentId, 1).state, 1);
    }

    function consumePythonGolden(bool official) private returns (Wallet) {
        address target = address(0x1212121212121212121212121212121212121212);
        vm.etch(target, address(registry).code);
        Wallet goldenRegistry = Wallet(target);
        vm.prank(a);
        bytes32 id = goldenRegistry.propose(
            Golden.proposal(), Golden.key_proof(), Golden.KEY_PROOF_SIGNATURE
        );
        vm.prank(a);
        goldenRegistry.approve(id);
        vm.prank(b);
        goldenRegistry.approve(id);
        Registry.Publish memory m = official ? Golden.official_document() : Golden.payment_request();
        goldenRegistry.publish(
            m, official ? Golden.OFFICIAL_DOCUMENT_SIGNATURE : Golden.PAYMENT_REQUEST_SIGNATURE
        );
        assertEq(goldenRegistry.getDocument(m.documentId, 1).originalHash, m.originalHash);
        assertEq(goldenRegistry.nextNonce(m.issuerId), 1);
        return goldenRegistry;
    }

    function testPythonPaymentGoldenIsConsumedByActualPublicationCode() public {
        consumePythonGolden(false);
    }

    function testPythonOfficialGoldenIsConsumedByActualPublicationCode() public {
        consumePythonGolden(true);
    }

    function testFuzzDocumentIdBindsIssuerAndDocKey(bytes32 docKey) public {
        Registry.Publish memory m = Golden.payment_request();
        m.docKey = docKey;
        m.documentId = keccak256(abi.encode(m.issuerId, docKey));
        registry.publish(m, signature(m, 1));
        assertEq(registry.getDocument(m.documentId, 1).docKey, docKey);
        assertEq(registry.nextNonce(m.issuerId), 1);
    }

    event DocumentSuperseded(
        bytes32 indexed documentId, uint64 indexed version, uint64 replacement
    );
    event DocumentRevoked(
        bytes32 indexed documentId, uint64 indexed version, bytes32 indexed issuerId
    );

    function revokeMessage(Registry.Publish memory m, uint256 nonce)
        private
        pure
        returns (Registry.Revoke memory)
    {
        return Registry.Revoke(
            2, m.issuerId, m.docKey, m.documentId, m.version, m.keyId, nonce, m.deadline
        );
    }

    function revokeSignature(Registry.Revoke memory m, uint256 key)
        private
        view
        returns (bytes memory)
    {
        return signHash(
            keccak256(
                abi.encode(
                    keccak256(
                        "Revoke(uint8 action,bytes32 issuerId,bytes32 docKey,bytes32 documentId,uint64 version,bytes32 keyId,uint256 nonce,uint64 deadline)"
                    ),
                    m
                )
            ),
            key,
            block.chainid,
            address(registry)
        );
    }

    function publishFirst() private returns (Registry.Publish memory m) {
        m = Golden.payment_request();
        registry.publish(m, signature(m, 1));
    }

    function nextVersion(Registry.Publish memory m) private pure returns (Registry.Publish memory) {
        // Memory structs alias on internal calls; keep the original version's expectations intact.
        Registry.Publish memory next = abi.decode(abi.encode(m), (Registry.Publish));
        ++next.version;
        ++next.nonce;
        next.originalHash = sha256(abi.encode("synthetic original", next.version));
        return next;
    }

    function testNextVersionAtomicallySupersedesWithoutChangingOriginalCommitments() public {
        Registry.Publish memory first = publishFirst();
        Registry.DocumentVersion memory old = registry.getDocument(first.documentId, 1);
        Registry.Publish memory second = nextVersion(first);
        bytes memory signed = signature(second, 1);
        vm.roll(20);
        vm.expectEmit(true, true, false, true, address(registry));
        emit DocumentSuperseded(first.documentId, 1, 2);
        vm.expectEmit(true, true, true, true, address(registry));
        emit DocumentPublished(first.documentId, 2, first.issuerId);
        registry.publish(second, signed);
        assertEq(registry.latestVersion(first.documentId), 2);
        assertEq(registry.getDocument(first.documentId, 2).state, 1);
        assertEq(registry.getDocument(first.documentId, 2).publishedBlock, 20);
        old.state = 3;
        assertEq(
            keccak256(abi.encode(registry.getDocument(first.documentId, 1))),
            keccak256(abi.encode(old))
        );
        assertEq(registry.nextNonce(first.issuerId), 2);
    }

    function testCompetingNextVersionOnlyOneCanCommit() public {
        Registry.Publish memory m = nextVersion(publishFirst());
        bytes memory winner = signature(m, 1);
        m.originalHash = sha256("competing version");
        bytes memory loser = signature(m, 1);
        m.originalHash = sha256(abi.encode("synthetic original", m.version));
        registry.publish(m, winner);
        m.originalHash = sha256("competing version");
        vm.expectRevert(Wallet.VersionConflict.selector);
        registry.publish(m, loser);
        assertEq(
            registry.getDocument(m.documentId, 2).originalHash,
            sha256(abi.encode("synthetic original", m.version))
        );
        assertEq(registry.nextNonce(m.issuerId), 2);
    }

    function testVersionGapAndFailedSuccessorPreserveAllPriorState() public {
        Registry.Publish memory first = publishFirst();
        Registry.Publish memory m = nextVersion(first);
        m.version = 3;
        bytes memory signed = signature(m, 1);
        vm.expectRevert(Wallet.VersionConflict.selector);
        registry.publish(m, signed);
        m.version = 2;
        signed = signature(m, 2);
        vm.expectRevert(Wallet.InvalidPublicationSignature.selector);
        registry.publish(m, signed);
        signed = signature(m, 1);
        vm.roll(0);
        vm.expectRevert(Governance.InvalidBlockNumber.selector);
        registry.publish(m, signed);
        assertEq(registry.latestVersion(first.documentId), 1);
        assertEq(registry.getDocument(first.documentId, 1).state, 1);
        assertEq(registry.getDocument(first.documentId, 1).originalHash, first.originalHash);
        assertEq(registry.nextNonce(first.issuerId), 1);
        vm.expectRevert(Wallet.UnknownDocument.selector);
        registry.getDocument(first.documentId, 2);
    }

    function testRelayedRevocationConsumesNonceAndPreservesCommitments() public {
        Registry.Publish memory m = publishFirst();
        Registry.DocumentVersion memory old = registry.getDocument(m.documentId, 1);
        Registry.Revoke memory r = revokeMessage(m, 1);
        bytes memory signed = revokeSignature(r, 1);
        vm.expectEmit(true, true, true, true, address(registry));
        emit DocumentRevoked(m.documentId, 1, m.issuerId);
        vm.prank(vm.addr(999));
        registry.revoke(r, signed);
        old.state = 2;
        assertEq(
            keccak256(abi.encode(registry.getDocument(m.documentId, 1))), keccak256(abi.encode(old))
        );
        assertEq(registry.nextNonce(m.issuerId), 2);
        assertEq(registry.governanceNonce(m.issuerId), 1);
        assertEq(registry.latestVersion(m.documentId), 1);
    }

    function testRevokedLatestNeverRevivesOlderVersion() public {
        Registry.Publish memory m = nextVersion(publishFirst());
        registry.publish(m, signature(m, 1));
        Registry.Revoke memory r = revokeMessage(m, 2);
        registry.revoke(r, revokeSignature(r, 1));
        assertEq(registry.getDocument(m.documentId, 2).state, 2);
        assertEq(registry.getDocument(m.documentId, 1).state, 3);
        assertEq(registry.latestVersion(m.documentId), 2);
        vm.warp(m.expiresAt + 1);
        vm.prank(a);
        registry.suspendIssuer(m.issuerId, keccak256("OTHER"));
        assertEq(registry.getDocument(m.documentId, 2).state, 2);
        assertEq(registry.getDocument(m.documentId, 1).state, 3);
    }

    function testSupersededVersionCanBeRevokedWithoutAffectingLatest() public {
        Registry.Publish memory first = publishFirst();
        Registry.Publish memory second = nextVersion(first);
        registry.publish(second, signature(second, 1));
        Registry.Revoke memory r = revokeMessage(first, 2);
        registry.revoke(r, revokeSignature(r, 1));
        assertEq(registry.getDocument(first.documentId, 1).state, 2);
        assertEq(registry.getDocument(first.documentId, 2).state, 1);
        assertEq(registry.latestVersion(first.documentId), 2);
    }

    function testPublicationAfterRevokedLatestAdvancesWithoutRevival() public {
        Registry.Publish memory first = publishFirst();
        Registry.Revoke memory r = revokeMessage(first, 1);
        registry.revoke(r, revokeSignature(r, 1));
        Registry.Publish memory second = nextVersion(first);
        second.nonce = 2;
        registry.publish(second, signature(second, 1));
        assertEq(registry.getDocument(first.documentId, 1).state, 3);
        assertEq(registry.getDocument(first.documentId, 1).originalHash, first.originalHash);
        assertEq(registry.getDocument(first.documentId, 2).state, 1);
        assertEq(registry.latestVersion(first.documentId), 2);
    }

    function testRevocationReplayAndFreshNonceRepeatFailWithoutConsumption() public {
        Registry.Publish memory m = publishFirst();
        Registry.Revoke memory r = revokeMessage(m, 1);
        bytes memory signed = revokeSignature(r, 1);
        registry.revoke(r, signed);
        vm.expectRevert(Wallet.NonceAlreadyUsed.selector);
        registry.revoke(r, signed);
        r.nonce = 2;
        signed = revokeSignature(r, 1);
        vm.expectRevert(Wallet.DocumentAlreadyRevoked.selector);
        registry.revoke(r, signed);
        assertEq(registry.nextNonce(m.issuerId), 2);
    }

    function testPublishAndRevokeShareOneNonceWhenPublicationWins() public {
        Registry.Publish memory first = publishFirst();
        Registry.Revoke memory r = revokeMessage(first, 1);
        bytes memory signed = revokeSignature(r, 1);
        Registry.Publish memory second = nextVersion(first);
        registry.publish(second, signature(second, 1));
        vm.expectRevert(Wallet.NonceAlreadyUsed.selector);
        registry.revoke(r, signed);
        assertEq(registry.getDocument(first.documentId, 1).state, 3);
        assertEq(registry.nextNonce(first.issuerId), 2);
    }

    function testPublishAndRevokeShareOneNonceWhenRevocationWins() public {
        Registry.Publish memory first = publishFirst();
        Registry.Publish memory second = nextVersion(first);
        bytes memory signed = signature(second, 1);
        Registry.Revoke memory r = revokeMessage(first, 1);
        registry.revoke(r, revokeSignature(r, 1));
        vm.expectRevert(Wallet.NonceAlreadyUsed.selector);
        registry.publish(second, signed);
        assertEq(registry.latestVersion(first.documentId), 1);
        assertEq(registry.getDocument(first.documentId, 1).state, 2);
        assertEq(registry.nextNonce(first.issuerId), 2);
    }

    function testSuspendedCurrentKeyMayRevokeButCannotPublish() public {
        Registry.Publish memory first = publishFirst();
        vm.prank(a);
        registry.suspendIssuer(first.issuerId, keccak256("OTHER"));
        Registry.Publish memory second = nextVersion(first);
        bytes memory signed = signature(second, 1);
        vm.expectRevert(Wallet.IssuerNotActive.selector);
        registry.publish(second, signed);
        Registry.Revoke memory r = revokeMessage(first, 1);
        registry.revoke(r, revokeSignature(r, 1));
        assertEq(registry.getDocument(first.documentId, 1).state, 2);
        (uint8 state,,,) = registry.getIssuer(first.issuerId);
        assertEq(state, 2);
    }

    function testCompromisedKeyMustRotateBeforeRevocationWhileStillSuspended() public {
        Registry.Publish memory first = publishFirst();
        vm.prank(a);
        registry.suspendIssuer(first.issuerId, keccak256("KEY_COMPROMISE"));
        Registry.Revoke memory r = revokeMessage(first, 1);
        bytes memory signed = revokeSignature(r, 1);
        vm.expectRevert(Wallet.KeyNotActive.selector);
        registry.revoke(r, signed);
        Registry.GovernanceProposal memory p = Golden.proposal();
        p.action = 2;
        p.keyId = keccak256("recovery key");
        p.signer = vm.addr(2);
        p.nonce = registry.governanceNonce(p.issuerId);
        vm.roll(20);
        register(p);
        r.keyId = p.keyId;
        registry.revoke(r, revokeSignature(r, 2));
        assertEq(registry.getDocument(first.documentId, 1).state, 2);
        assertEq(registry.getDocument(first.documentId, 1).keyId, first.keyId);
        assertEq(registry.getKey(first.keyId).retiredBlock, 20);
        assertGt(registry.getKey(first.keyId).compromiseBlock, 0);
        (uint8 state,,,) = registry.getIssuer(first.issuerId);
        assertEq(state, 2);
    }

    function testCurrentKeyAfterNormalRotationCanRevokeOldPublication() public {
        Registry.Publish memory first = publishFirst();
        Registry.GovernanceProposal memory p = Golden.proposal();
        p.action = 2;
        p.keyId = keccak256("normal replacement");
        p.signer = vm.addr(2);
        p.nonce = registry.governanceNonce(p.issuerId);
        register(p);
        Registry.Revoke memory r = revokeMessage(first, 1);
        bytes memory signed = revokeSignature(r, 1);
        vm.expectRevert(Wallet.KeyNotActive.selector);
        registry.revoke(r, signed);
        r.keyId = p.keyId;
        registry.revoke(r, revokeSignature(r, 2));
        assertEq(registry.getDocument(first.documentId, 1).keyId, first.keyId);
        assertEq(registry.getDocument(first.documentId, 1).state, 2);
    }

    function testEveryRevokeFieldIsBoundAndFailuresPreserveState() public {
        Registry.Publish memory first = publishFirst();
        Registry.Revoke memory r = revokeMessage(first, 1);
        bytes memory signed = revokeSignature(r, 1);
        for (uint256 i; i < 8; ++i) {
            bytes memory input = abi.encodeCall(Registry.revoke, (r, signed));
            uint256 offset = 36 + i * 32;
            assembly ("memory-safe") {
                mstore(add(input, offset), xor(mload(add(input, offset)), 1))
            }
            (bool ok,) = address(registry).call(input);
            assertFalse(ok);
            assertEq(registry.getDocument(first.documentId, 1).state, 1);
            assertEq(registry.nextNonce(first.issuerId), 1);
        }
    }

    function testOtherIssuerAndCallerCannotRevokeOwnIssuerDocument() public {
        Registry.Publish memory first = publishFirst();
        Registry.GovernanceProposal memory p = Golden.proposal();
        p.issuerId = keccak256("other issuer");
        p.keyId = keccak256("other key");
        p.signer = vm.addr(2);
        register(p);
        Registry.Revoke memory r = revokeMessage(first, 1);
        bytes memory signed = revokeSignature(r, 2);
        vm.prank(a);
        vm.expectRevert(Wallet.InvalidRevocationSignature.selector);
        registry.revoke(r, signed);
        r.issuerId = p.issuerId;
        r.keyId = p.keyId;
        r.nonce = 0;
        signed = revokeSignature(r, 2);
        vm.expectRevert(Wallet.InvalidDocumentId.selector);
        registry.revoke(r, signed);
        assertEq(registry.getDocument(first.documentId, 1).state, 1);
        assertEq(registry.nextNonce(first.issuerId), 1);
    }

    function testRevokeDeadlineBoundaryAndExpiredDocumentRevocation() public {
        Registry.Publish memory first = publishFirst();
        Registry.Revoke memory r = revokeMessage(first, 1);
        bytes memory signed = revokeSignature(r, 1);
        vm.warp(r.deadline);
        vm.expectRevert(Wallet.SignatureExpired.selector);
        registry.revoke(r, signed);
        vm.warp(first.expiresAt + 1);
        assertEq(registry.getDocument(first.documentId, 1).state, 1);
        r.deadline = uint64(block.timestamp + 300);
        registry.revoke(r, revokeSignature(r, 1));
        assertEq(registry.getDocument(first.documentId, 1).state, 2);
    }

    function testMalformedRevocationAndUnknownVersionDoNotConsumeNonce() public {
        Registry.Publish memory first = publishFirst();
        for (uint256 i; i < 4; ++i) {
            Registry.Revoke memory r = revokeMessage(first, 1);
            if (i == 0) r.action = 1;
            if (i == 1) r.version = 0;
            if (i == 2) r.version = uint64(2 ** 53);
            if (i == 3) r.deadline = uint64(2 ** 53);
            bytes memory signed = revokeSignature(r, 1);
            vm.expectRevert(Wallet.InvalidRevocation.selector);
            registry.revoke(r, signed);
        }
        Registry.Revoke memory missing = revokeMessage(first, 1);
        missing.version = 2;
        bytes memory missingSignature = revokeSignature(missing, 1);
        vm.expectRevert(Wallet.UnknownDocument.selector);
        registry.revoke(missing, missingSignature);
        assertEq(registry.nextNonce(first.issuerId), 1);
    }

    function testRevocationWrongDomainAndMalformedSignatureFail() public {
        Registry.Publish memory first = publishFirst();
        Registry.Revoke memory r = revokeMessage(first, 1);
        bytes32 hash = keccak256(
            abi.encode(
                keccak256(
                    "Revoke(uint8 action,bytes32 issuerId,bytes32 docKey,bytes32 documentId,uint64 version,bytes32 keyId,uint256 nonce,uint64 deadline)"
                ),
                r
            )
        );
        bytes memory signed = signHash(hash, 1, block.chainid + 1, address(registry));
        vm.expectRevert(Wallet.InvalidRevocationSignature.selector);
        registry.revoke(r, signed);
        signed = signHash(hash, 1, block.chainid, address(0x1234));
        vm.expectRevert(Wallet.InvalidRevocationSignature.selector);
        registry.revoke(r, signed);
        vm.expectRevert(Wallet.InvalidRevocationSignature.selector);
        registry.revoke(r, hex"00");
        signed = revokeSignature(r, 1);
        bytes32 sigR;
        bytes32 sigS;
        assembly ("memory-safe") {
            sigR := mload(add(signed, 32))
            sigS := mload(add(signed, 64))
        }
        uint256 order = 0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141;
        bytes memory highS = abi.encodePacked(
            sigR, bytes32(order - uint256(sigS)), uint8(signed[64]) == 27 ? uint8(28) : uint8(27)
        );
        vm.expectRevert(Wallet.InvalidRevocationSignature.selector);
        registry.revoke(r, highS);
        signed[64] = 0;
        vm.expectRevert(Wallet.InvalidRevocationSignature.selector);
        registry.revoke(r, signed);
        assertEq(registry.nextNonce(first.issuerId), 1);
    }

    function testPythonRevokeGoldenIsConsumedByActualLifecycleCode() public {
        Wallet goldenRegistry = consumePythonGolden(false);
        Registry.Revoke memory r = Golden.revoke();
        goldenRegistry.revoke(r, Golden.REVOKE_SIGNATURE);
        assertEq(goldenRegistry.getDocument(r.documentId, 1).state, 2);
        assertEq(goldenRegistry.nextNonce(r.issuerId), 2);
    }

    function testFuzzVersionHistoryNeverRevivesAfterLatestRevocation(uint8 count) public {
        count = uint8(bound(count, 2, 8));
        Registry.Publish memory first = publishFirst();
        Registry.Publish memory m = first;
        for (uint64 version = 2; version <= count; ++version) {
            m = nextVersion(m);
            registry.publish(m, signature(m, 1));
            assertEq(registry.latestVersion(m.documentId), version);
            assertEq(registry.getDocument(m.documentId, version - 1).state, 3);
        }
        Registry.Revoke memory r = revokeMessage(m, count);
        registry.revoke(r, revokeSignature(r, 1));
        assertEq(registry.latestVersion(m.documentId), count);
        assertEq(registry.getDocument(m.documentId, count).state, 2);
        assertEq(registry.getDocument(first.documentId, 1).originalHash, first.originalHash);
        for (uint64 version = 1; version < count; ++version) {
            assertEq(registry.getDocument(m.documentId, version).state, 3);
        }
    }
}
