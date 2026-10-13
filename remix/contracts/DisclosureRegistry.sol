// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "./interfaces/IUniCredentialSBT.sol";

/**
 * @title DisclosureRegistry
 * @notice Records student consent separately from the credential contract.
 * @dev This registry is an auditable consent signal, not encryption. Private
 *      fields remain in MySQL/private storage and are released by FastAPI only
 *      after the application verifies this registry or a one-time share link.
 */
contract DisclosureRegistry {
    IUniCredentialSBT public immutable credential;

    // type(uint64).max means no expiry; zero means no active grant.
    mapping(uint256 tokenId => mapping(address verifier => uint64 expiresAt))
        private _grants;

    error ZeroAddress();
    error NotCredentialHolder();
    error InvalidExpiry();

    event AccessGranted(
        uint256 indexed tokenId,
        address indexed student,
        address indexed verifier,
        uint64 expiresAt
    );
    event AccessRevoked(
        uint256 indexed tokenId,
        address indexed student,
        address indexed verifier
    );

    constructor(address credentialAddress) {
        if (credentialAddress == address(0)) revert ZeroAddress();
        credential = IUniCredentialSBT(credentialAddress);
    }

    function grantAccess(
        uint256 tokenId,
        address verifier,
        uint64 expiresAt
    ) external {
        if (credential.ownerOf(tokenId) != msg.sender) {
            revert NotCredentialHolder();
        }
        if (verifier == address(0)) revert ZeroAddress();
        if (expiresAt != 0 && expiresAt <= block.timestamp) {
            revert InvalidExpiry();
        }

        uint64 storedExpiry = expiresAt == 0
            ? type(uint64).max
            : expiresAt;
        _grants[tokenId][verifier] = storedExpiry;
        emit AccessGranted(tokenId, msg.sender, verifier, storedExpiry);
    }

    function revokeAccess(uint256 tokenId, address verifier) external {
        if (credential.ownerOf(tokenId) != msg.sender) {
            revert NotCredentialHolder();
        }
        delete _grants[tokenId][verifier];
        emit AccessRevoked(tokenId, msg.sender, verifier);
    }

    function hasAccess(
        uint256 tokenId,
        address verifier
    ) public view returns (bool) {
        address student = credential.ownerOf(tokenId);
        if (verifier == student) return true;
        uint64 expiresAt = _grants[tokenId][verifier];
        return expiresAt != 0 && expiresAt >= block.timestamp;
    }

    function accessExpiresAt(
        uint256 tokenId,
        address verifier
    ) external view returns (uint64) {
        return _grants[tokenId][verifier];
    }
}
