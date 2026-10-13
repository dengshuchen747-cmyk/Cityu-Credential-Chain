// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "remix_tests.sol";
import "../contracts/UniCredentialSBT.sol";

/**
 * Remix Unit Testing treats every compiled contract in a selected test file
 * as a test suite. Keep this file to one contract and make every public test
 * function parameterless.
 */
contract UniCredentialSBTTest {
    UniCredentialSBT private credential;

    function beforeEach() public {
        credential = new UniCredentialSBT(address(this));
        credential.grantRole(credential.ISSUER_ROLE(), address(this));
    }

    function testIssueAndVerify() public {
        bytes32 dataHash = keccak256("CITYU-2026-001");
        uint256 tokenId = credential.issueCredential(
            address(this),
            dataHash,
            "ipfs://credential-001"
        );

        Assert.equal(tokenId, 1, "first token id should be one");
        Assert.equal(
            credential.ownerOf(tokenId),
            address(this),
            "test holder should own credential"
        );

        (
            bool valid,
            bool hashMatches,
            bool revoked,
            address student,
            address issuer,
            uint64 issuedAt,

        ) = credential.verifyCredential(tokenId, dataHash);

        Assert.ok(valid, "credential should be valid");
        Assert.ok(hashMatches, "hash should match");
        Assert.ok(!revoked, "credential should not be revoked");
        Assert.equal(student, address(this), "student should match");
        Assert.equal(issuer, address(this), "issuer should match");
        Assert.ok(issuedAt > 0, "issuedAt should be set");
    }

    function testUnauthorizedIssuerRejected() public {
        credential.revokeRole(credential.ISSUER_ROLE(), address(this));
        bool reverted;
        try
            credential.issueCredential(
                address(0x1234),
                keccak256("unauthorized"),
                "ipfs://unauthorized"
            )
        returns (uint256) {
            reverted = false;
        } catch {
            reverted = true;
        }
        Assert.ok(reverted, "unauthorized issuer must be rejected");
    }

    function testDuplicateHashRejected() public {
        bytes32 dataHash = keccak256("unique");
        credential.issueCredential(address(this), dataHash, "ipfs://one");
        bool reverted;
        try
            credential.issueCredential(
                address(0xBEEF),
                dataHash,
                "ipfs://two"
            )
        returns (uint256) {
            reverted = false;
        } catch {
            reverted = true;
        }
        Assert.ok(reverted, "duplicate hash must be rejected");
    }

    function testCredentialIsSoulbound() public {
        uint256 tokenId = credential.issueCredential(
            address(this),
            keccak256("soulbound"),
            "ipfs://soulbound"
        );
        bool reverted;
        try credential.transferFrom(address(this), address(0xBEEF), tokenId) {
            reverted = false;
        } catch {
            reverted = true;
        }
        Assert.ok(reverted, "credential transfer must revert");
    }

    function testIssuerCanRevoke() public {
        bytes32 dataHash = keccak256("revoke-me");
        uint256 tokenId = credential.issueCredential(
            address(this),
            dataHash,
            "ipfs://revoke"
        );
        credential.revokeCredential(tokenId, keccak256("wrong recipient"));
        (bool valid, , bool revoked, , , , ) = credential.verifyCredential(
            tokenId,
            dataHash
        );
        Assert.ok(revoked, "credential should be revoked");
        Assert.ok(!valid, "revoked credential must be invalid");
    }
}
