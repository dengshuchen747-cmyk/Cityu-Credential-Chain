// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "@openzeppelin/contracts@5.0.2/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts@5.0.2/access/AccessControl.sol";

/**
 * @title UniCredentialSBT
 * @notice A deliberately small, non-transferable academic credential token.
 * @dev Campaigns, applications, evidence and PII belong in the FastAPI/MySQL
 *      application. Only integrity proofs and lifecycle state are stored here.
 */
contract UniCredentialSBT is ERC721, AccessControl {
    bytes32 public constant ISSUER_ROLE = keccak256("ISSUER_ROLE");

    struct Credential {
        bytes32 dataHash;
        bytes32 revocationReasonHash;
        address issuer;
        uint64 issuedAt;
        uint64 revokedAt;
        bool revoked;
        string metadataURI;
    }

    uint256 private _nextTokenId = 1;
    mapping(uint256 tokenId => Credential credential) private _credentials;
    mapping(bytes32 dataHash => uint256 tokenId) public tokenIdByDataHash;

    error ZeroAddress();
    error EmptyDataHash();
    error DuplicateDataHash();
    error Soulbound();
    error AlreadyRevoked();
    error NotCredentialIssuerOrAdmin();

    event CredentialIssued(
        uint256 indexed tokenId,
        address indexed student,
        address indexed issuer,
        bytes32 dataHash,
        string metadataURI
    );
    event CredentialRevoked(
        uint256 indexed tokenId,
        address indexed revokedBy,
        bytes32 reasonHash
    );

    constructor(address admin) ERC721("CityU Credential", "CITYU-SBT") {
        if (admin == address(0)) revert ZeroAddress();
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
    }

    function issueCredential(
        address student,
        bytes32 dataHash,
        string calldata metadataURI
    ) external onlyRole(ISSUER_ROLE) returns (uint256 tokenId) {
        if (student == address(0)) revert ZeroAddress();
        if (dataHash == bytes32(0)) revert EmptyDataHash();
        if (tokenIdByDataHash[dataHash] != 0) revert DuplicateDataHash();

        tokenId = _nextTokenId++;
        tokenIdByDataHash[dataHash] = tokenId;
        _credentials[tokenId] = Credential({
            dataHash: dataHash,
            revocationReasonHash: bytes32(0),
            issuer: msg.sender,
            issuedAt: uint64(block.timestamp),
            revokedAt: 0,
            revoked: false,
            metadataURI: metadataURI
        });
        // Credentials are intentionally non-transferable. Using _mint avoids
        // an external receiver callback during issuance and also keeps Remix
        // unit tests deterministic when the test contract is the holder.
        _mint(student, tokenId);

        emit CredentialIssued(tokenId, student, msg.sender, dataHash, metadataURI);
    }

    function revokeCredential(uint256 tokenId, bytes32 reasonHash) external {
        ownerOf(tokenId);
        Credential storage credential = _credentials[tokenId];
        if (
            msg.sender != credential.issuer &&
            !hasRole(DEFAULT_ADMIN_ROLE, msg.sender)
        ) revert NotCredentialIssuerOrAdmin();
        if (credential.revoked) revert AlreadyRevoked();

        credential.revoked = true;
        credential.revokedAt = uint64(block.timestamp);
        credential.revocationReasonHash = reasonHash;

        emit CredentialRevoked(tokenId, msg.sender, reasonHash);
    }

    function getCredential(
        uint256 tokenId
    ) external view returns (Credential memory) {
        ownerOf(tokenId);
        return _credentials[tokenId];
    }

    function verifyCredential(
        uint256 tokenId,
        bytes32 submittedHash
    )
        external
        view
        returns (
            bool valid,
            bool hashMatches,
            bool revoked,
            address student,
            address issuer,
            uint64 issuedAt,
            string memory metadataURI
        )
    {
        student = _ownerOf(tokenId);
        if (student == address(0)) {
            return (false, false, false, address(0), address(0), 0, "");
        }

        Credential storage credential = _credentials[tokenId];
        hashMatches = credential.dataHash == submittedHash;
        revoked = credential.revoked;
        valid = hashMatches && !revoked;
        issuer = credential.issuer;
        issuedAt = credential.issuedAt;
        metadataURI = credential.metadataURI;
    }

    function isIssuer(address account) external view returns (bool) {
        return hasRole(ISSUER_ROLE, account);
    }

    function credentialCount() external view returns (uint256) {
        return _nextTokenId - 1;
    }

    function tokenURI(
        uint256 tokenId
    ) public view override returns (string memory) {
        ownerOf(tokenId);
        return _credentials[tokenId].metadataURI;
    }

    function supportsInterface(
        bytes4 interfaceId
    ) public view override(ERC721, AccessControl) returns (bool) {
        return super.supportsInterface(interfaceId);
    }

    /**
     * @dev Minting (from == 0) is allowed. Every transfer between non-zero
     *      addresses is rejected, which makes the credential soulbound.
     */
    function _update(
        address to,
        uint256 tokenId,
        address auth
    ) internal override returns (address from) {
        from = _ownerOf(tokenId);
        if (from != address(0) && to != address(0)) revert Soulbound();
        return super._update(to, tokenId, auth);
    }
}
