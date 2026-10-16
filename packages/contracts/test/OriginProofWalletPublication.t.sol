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
        vm.expectRevert(Wallet.NonceAlreadyUsed.selector);
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

    function testOnlyInitialVersionAndExactNonceAreAccepted() public {
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

    function testAbsentVersionAndRevocationAreNotSuccess() public {
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

    function consumePythonGolden(bool official) private {
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
}
