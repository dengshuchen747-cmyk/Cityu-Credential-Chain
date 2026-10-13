// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "remix_tests.sol";
import "../contracts/UniCredentialSBT.sol";
import "../contracts/DisclosureRegistry.sol";

contract DisclosureRegistryTest {
    UniCredentialSBT private credential;
    DisclosureRegistry private registry;
    uint256 private tokenId;
    address private verifier;

    function beforeEach() public {
        credential = new UniCredentialSBT(address(this));
        credential.grantRole(credential.ISSUER_ROLE(), address(this));
        tokenId = credential.issueCredential(
            address(this),
            keccak256("disclosure-test"),
            "ipfs://disclosure-test"
        );
        registry = new DisclosureRegistry(address(credential));
        verifier = address(0xCAFE);
    }

    function testHolderCanGrantAndRevoke() public {
        registry.grantAccess(tokenId, verifier, 0);
        Assert.ok(
            registry.hasAccess(tokenId, verifier),
            "verifier should have access"
        );

        registry.revokeAccess(tokenId, verifier);
        Assert.ok(
            !registry.hasAccess(tokenId, verifier),
            "verifier access should be removed"
        );
    }

    function testPastExpiryRejected() public {
        bool reverted;
        try registry.grantAccess(tokenId, verifier, 1) {
            reverted = false;
        } catch {
            reverted = true;
        }
        Assert.ok(reverted, "past expiry must be rejected");
    }
}
