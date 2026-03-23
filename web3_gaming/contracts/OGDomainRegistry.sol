// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Strings.sol";

/// @title OG Domain Registry - .og TLD for Web3 Gaming
/// @notice Register and manage .og domains as NFTs with gaming profile integration
contract OGDomainRegistry is ERC721, Ownable {
    using Strings for uint256;

    struct Domain {
        string name;
        address resolver;
        uint256 expiry;
        mapping(string => string) records; // key-value text records
    }

    struct GamerProfile {
        string displayName;
        uint256 level;
        uint256 xp;
        uint256 gamesPlayed;
        uint256 wins;
        uint256[] ownedAssets; // token IDs from GameAssetNFT
    }

    uint256 public constant MIN_REGISTRATION_DURATION = 365 days;
    uint256 public constant GRACE_PERIOD = 90 days;

    uint256 public pricePerYear = 0.01 ether;
    uint256 private _nextTokenId;

    // domain name hash => token id
    mapping(bytes32 => uint256) public domainToToken;
    // token id => domain data
    mapping(uint256 => Domain) private _domains;
    // domain name hash => gamer profile
    mapping(bytes32 => GamerProfile) public gamerProfiles;
    // address => primary domain hash
    mapping(address => bytes32) public primaryDomain;
    // reverse: address => domain name
    mapping(address => string) public reverseLookup;

    event DomainRegistered(string indexed name, address indexed owner, uint256 expiry);
    event DomainRenewed(string indexed name, uint256 newExpiry);
    event RecordSet(string indexed name, string key, string value);
    event GamerProfileUpdated(string indexed domain, string displayName, uint256 level);
    event PrimaryDomainSet(address indexed owner, string domain);

    constructor() ERC721("OG Domain", ".og") Ownable(msg.sender) {}

    /// @notice Hash a domain name for mapping lookups
    function namehash(string memory name) public pure returns (bytes32) {
        return keccak256(abi.encodePacked(name, ".og"));
    }

    /// @notice Register a new .og domain
    function register(string calldata name, uint256 durationYears) external payable {
        require(bytes(name).length >= 3, "Name too short");
        require(bytes(name).length <= 32, "Name too long");
        require(durationYears >= 1, "Min 1 year");
        require(msg.value >= pricePerYear * durationYears, "Insufficient payment");

        bytes32 node = namehash(name);
        uint256 existingToken = domainToToken[node];

        if (existingToken != 0) {
            Domain storage d = _domains[existingToken];
            require(block.timestamp > d.expiry + GRACE_PERIOD, "Domain taken");
            // Expired + grace period passed, burn old token
            _burn(existingToken);
        }

        _nextTokenId++;
        uint256 tokenId = _nextTokenId;

        _mint(msg.sender, tokenId);
        domainToToken[node] = tokenId;

        Domain storage domain = _domains[tokenId];
        domain.name = name;
        domain.resolver = msg.sender;
        domain.expiry = block.timestamp + (durationYears * 365 days);

        // Initialize gamer profile
        GamerProfile storage profile = gamerProfiles[node];
        profile.displayName = name;
        profile.level = 1;

        // Set as primary if user has none
        if (primaryDomain[msg.sender] == bytes32(0)) {
            primaryDomain[msg.sender] = node;
            reverseLookup[msg.sender] = string(abi.encodePacked(name, ".og"));
            emit PrimaryDomainSet(msg.sender, name);
        }

        emit DomainRegistered(name, msg.sender, domain.expiry);
    }

    /// @notice Renew a domain you own
    function renew(string calldata name, uint256 additionalYears) external payable {
        require(msg.value >= pricePerYear * additionalYears, "Insufficient payment");
        bytes32 node = namehash(name);
        uint256 tokenId = domainToToken[node];
        require(tokenId != 0, "Domain not registered");
        require(ownerOf(tokenId) == msg.sender, "Not owner");

        Domain storage domain = _domains[tokenId];
        uint256 base = block.timestamp > domain.expiry ? block.timestamp : domain.expiry;
        domain.expiry = base + (additionalYears * 365 days);

        emit DomainRenewed(name, domain.expiry);
    }

    /// @notice Set a text record on your domain
    function setRecord(string calldata name, string calldata key, string calldata value) external {
        bytes32 node = namehash(name);
        uint256 tokenId = domainToToken[node];
        require(ownerOf(tokenId) == msg.sender, "Not owner");
        _domains[tokenId].records[key] = value;
        emit RecordSet(name, key, value);
    }

    /// @notice Update the gamer profile linked to a domain
    function updateGamerProfile(
        string calldata name,
        string calldata displayName,
        uint256 xpGained,
        uint256 gamesPlayed,
        uint256 wins
    ) external {
        bytes32 node = namehash(name);
        uint256 tokenId = domainToToken[node];
        require(ownerOf(tokenId) == msg.sender, "Not owner");

        GamerProfile storage profile = gamerProfiles[node];
        if (bytes(displayName).length > 0) {
            profile.displayName = displayName;
        }
        profile.xp += xpGained;
        profile.gamesPlayed += gamesPlayed;
        profile.wins += wins;

        // Level up: every 1000 XP = 1 level
        uint256 newLevel = (profile.xp / 1000) + 1;
        if (newLevel > profile.level) {
            profile.level = newLevel;
        }

        emit GamerProfileUpdated(name, profile.displayName, profile.level);
    }

    /// @notice Set primary .og domain for reverse resolution
    function setPrimaryDomain(string calldata name) external {
        bytes32 node = namehash(name);
        uint256 tokenId = domainToToken[node];
        require(ownerOf(tokenId) == msg.sender, "Not owner");

        primaryDomain[msg.sender] = node;
        reverseLookup[msg.sender] = string(abi.encodePacked(name, ".og"));
        emit PrimaryDomainSet(msg.sender, name);
    }

    /// @notice Resolve a .og domain to an address
    function resolve(string calldata name) external view returns (address) {
        bytes32 node = namehash(name);
        uint256 tokenId = domainToToken[node];
        require(tokenId != 0, "Domain not registered");
        Domain storage domain = _domains[tokenId];
        require(block.timestamp <= domain.expiry, "Domain expired");
        return domain.resolver;
    }

    /// @notice Get domain expiry
    function getExpiry(string calldata name) external view returns (uint256) {
        bytes32 node = namehash(name);
        uint256 tokenId = domainToToken[node];
        require(tokenId != 0, "Domain not registered");
        return _domains[tokenId].expiry;
    }

    /// @notice Get a text record
    function getRecord(string calldata name, string calldata key) external view returns (string memory) {
        bytes32 node = namehash(name);
        uint256 tokenId = domainToToken[node];
        return _domains[tokenId].records[key];
    }

    /// @notice Get gamer profile for a domain
    function getGamerProfile(string calldata name)
        external
        view
        returns (string memory displayName, uint256 level, uint256 xp, uint256 gamesPlayed, uint256 wins)
    {
        bytes32 node = namehash(name);
        GamerProfile storage p = gamerProfiles[node];
        return (p.displayName, p.level, p.xp, p.gamesPlayed, p.wins);
    }

    /// @notice Owner can update pricing
    function setPrice(uint256 newPrice) external onlyOwner {
        pricePerYear = newPrice;
    }

    /// @notice Withdraw contract funds
    function withdraw() external onlyOwner {
        payable(owner()).transfer(address(this).balance);
    }
}
