// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

import {Test} from "forge-std/Test.sol";
import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import {IOriginProofWalletRegistry as Registry} from "../src/IOriginProofWalletRegistry.sol";
import {WalletGolden as Golden} from "./generated/WalletGolden.sol";

/// @notice Independent ABI/EIP-712 checks only; no Registry behavior is simulated.
contract WalletContractGoldenTest is Test {
    bytes32 internal constant PUBLISH_TYPEHASH = keccak256(
        "Publish(uint8 action,bytes32 issuerId,bytes32 docKey,bytes32 documentId,uint64 version,bytes32 keyId,bytes32 originalHash,bytes32 protectedHash,bytes32 contentSchema,bytes32 signatureSchema,uint8 originalHashAlgorithm,uint8 protectedHashAlgorithm,uint64 issuedAt,uint64 expiresAt,uint256 nonce,uint64 deadline)"
    );
    bytes32 internal constant REVOKE_TYPEHASH = keccak256(
        "Revoke(uint8 action,bytes32 issuerId,bytes32 docKey,bytes32 documentId,uint64 version,bytes32 keyId,uint256 nonce,uint64 deadline)"
    );
    bytes32 internal constant KEY_PROOF_TYPEHASH = keccak256(
        "KeyProof(uint8 action,bytes32 applicationId,bytes32 issuerId,address signer,bytes32 challengeNonce,uint64 deadline)"
    );

    function domain(uint256 chainId, address verifyingContract) internal pure returns (bytes32) {
        return keccak256(
            abi.encode(
                keccak256(
                    "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
                ),
                keccak256("OriginProof"),
                keccak256("1"),
                chainId,
                verifyingContract
            )
        );
    }

    function digest(bytes32 hash, uint256 chainId, address verifyingContract)
        internal
        pure
        returns (bytes32)
    {
        return keccak256(abi.encodePacked(hex"1901", domain(chainId, verifyingContract), hash));
    }

    function defaultDigest(bytes32 hash) internal pure returns (bytes32) {
        return digest(hash, 31337, address(0x1212121212121212121212121212121212121212));
    }

    function testGoldenPublicationHashesAndSigner() public pure {
        Registry.Publish memory payment = Golden.payment_request();
        bytes32 paymentDigest = defaultDigest(keccak256(abi.encode(PUBLISH_TYPEHASH, payment)));
        assertEq(payment.documentId, keccak256(abi.encode(payment.issuerId, payment.docKey)));
        assertEq(paymentDigest, Golden.PAYMENT_REQUEST_DIGEST);
        assertEq(ECDSA.recover(paymentDigest, Golden.PAYMENT_REQUEST_SIGNATURE), vm.addr(1));
        Registry.Publish memory official = Golden.official_document();
        bytes32 officialDigest = defaultDigest(keccak256(abi.encode(PUBLISH_TYPEHASH, official)));
        assertEq(officialDigest, Golden.OFFICIAL_DOCUMENT_DIGEST);
        assertEq(ECDSA.recover(officialDigest, Golden.OFFICIAL_DOCUMENT_SIGNATURE), vm.addr(1));
    }

    function testGoldenRevokeAndKeyProof() public pure {
        bytes32 revokeDigest =
            defaultDigest(keccak256(abi.encode(REVOKE_TYPEHASH, Golden.revoke())));
        bytes32 proofDigest =
            defaultDigest(keccak256(abi.encode(KEY_PROOF_TYPEHASH, Golden.key_proof())));
        assertEq(revokeDigest, Golden.REVOKE_DIGEST);
        assertEq(proofDigest, Golden.KEY_PROOF_DIGEST);
        assertEq(ECDSA.recover(revokeDigest, Golden.REVOKE_SIGNATURE), vm.addr(1));
        assertEq(ECDSA.recover(proofDigest, Golden.KEY_PROOF_SIGNATURE), vm.addr(1));
    }

    function testGovernanceProposalIdentifier() public pure {
        Registry.GovernanceProposal memory proposal = Golden.proposal();
        assertEq(
            keccak256(
                abi.encode(
                    uint256(31337), address(0x1212121212121212121212121212121212121212), proposal
                )
            ),
            Golden.PROPOSAL_ID
        );
    }

    function testDomainAndMessageChangesInvalidateExistingSignature() public pure {
        Registry.Publish memory payment = Golden.payment_request();
        bytes32 hash = keccak256(abi.encode(PUBLISH_TYPEHASH, payment));
        assertTrue(
            ECDSA.recover(
                digest(hash, 1, address(0x1212121212121212121212121212121212121212)),
                Golden.PAYMENT_REQUEST_SIGNATURE
            ) != vm.addr(1)
        );
        assertTrue(
            ECDSA.recover(
                digest(hash, 31337, address(0x3434343434343434343434343434343434343434)),
                Golden.PAYMENT_REQUEST_SIGNATURE
            ) != vm.addr(1)
        );
        payment.version = 2;
        assertTrue(
            ECDSA.recover(
                defaultDigest(keccak256(abi.encode(PUBLISH_TYPEHASH, payment))),
                Golden.PAYMENT_REQUEST_SIGNATURE
            ) != vm.addr(1)
        );
    }
}
