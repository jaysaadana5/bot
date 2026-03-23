// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC1155/ERC1155.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Strings.sol";

/// @title GameAssetNFT - Multi-token gaming assets with .og domain binding
/// @notice Manages in-game items, skins, achievements as ERC-1155 tokens
contract GameAssetNFT is ERC1155, Ownable {
    using Strings for uint256;

    enum AssetType { WEAPON, ARMOR, SKIN, CONSUMABLE, ACHIEVEMENT, LAND }

    struct Asset {
        string name;
        AssetType assetType;
        uint256 rarity;   // 1=Common, 2=Uncommon, 3=Rare, 4=Epic, 5=Legendary
        uint256 power;
        uint256 maxSupply;
        uint256 minted;
        uint256 price;
        bool tradeable;
        string gameId;     // which game this asset belongs to
    }

    struct Game {
        string name;
        address developer;
        bool active;
        uint256[] assetIds;
    }

    uint256 private _nextAssetId;
    string public baseURI;

    // asset id => asset metadata
    mapping(uint256 => Asset) public assets;
    // game id => game data
    mapping(string => Game) public games;
    // player address => game id => equipped asset ids
    mapping(address => mapping(string => uint256[])) public equippedAssets;
    // authorized game contracts that can mint/burn
    mapping(address => bool) public authorizedGames;

    event AssetCreated(uint256 indexed id, string name, AssetType assetType, uint256 rarity);
    event GameRegistered(string indexed gameId, string name, address developer);
    event AssetEquipped(address indexed player, string gameId, uint256 assetId);
    event AssetUnequipped(address indexed player, string gameId, uint256 assetId);
    event AssetMinted(address indexed to, uint256 indexed assetId, uint256 amount);

    constructor(string memory uri_) ERC1155(uri_) Ownable(msg.sender) {
        baseURI = uri_;
    }

    modifier onlyAuthorizedGame() {
        require(authorizedGames[msg.sender] || msg.sender == owner(), "Not authorized");
        _;
    }

    /// @notice Register a new game
    function registerGame(string calldata gameId, string calldata name) external {
        require(games[gameId].developer == address(0), "Game exists");
        Game storage g = games[gameId];
        g.name = name;
        g.developer = msg.sender;
        g.active = true;
        emit GameRegistered(gameId, name, msg.sender);
    }

    /// @notice Create a new asset type
    function createAsset(
        string calldata name,
        AssetType assetType,
        uint256 rarity,
        uint256 power,
        uint256 maxSupply,
        uint256 price,
        bool tradeable,
        string calldata gameId
    ) external returns (uint256) {
        require(games[gameId].developer == msg.sender || msg.sender == owner(), "Not game dev");

        _nextAssetId++;
        uint256 assetId = _nextAssetId;

        assets[assetId] = Asset({
            name: name,
            assetType: assetType,
            rarity: rarity,
            power: power,
            maxSupply: maxSupply,
            minted: 0,
            price: price,
            tradeable: tradeable,
            gameId: gameId
        });

        games[gameId].assetIds.push(assetId);
        emit AssetCreated(assetId, name, assetType, rarity);
        return assetId;
    }

    /// @notice Mint game assets to a player
    function mintAsset(address to, uint256 assetId, uint256 amount) external payable {
        Asset storage asset = assets[assetId];
        require(bytes(asset.name).length > 0, "Asset doesn't exist");
        require(asset.minted + amount <= asset.maxSupply, "Exceeds max supply");

        if (msg.sender != owner() && !authorizedGames[msg.sender]) {
            require(msg.value >= asset.price * amount, "Insufficient payment");
        }

        asset.minted += amount;
        _mint(to, assetId, amount, "");
        emit AssetMinted(to, assetId, amount);
    }

    /// @notice Equip an asset in a game
    function equipAsset(string calldata gameId, uint256 assetId) external {
        require(balanceOf(msg.sender, assetId) > 0, "Don't own asset");
        require(
            keccak256(bytes(assets[assetId].gameId)) == keccak256(bytes(gameId)),
            "Asset not for this game"
        );
        equippedAssets[msg.sender][gameId].push(assetId);
        emit AssetEquipped(msg.sender, gameId, assetId);
    }

    /// @notice Get equipped assets for a player in a game
    function getEquippedAssets(address player, string calldata gameId)
        external
        view
        returns (uint256[] memory)
    {
        return equippedAssets[player][gameId];
    }

    /// @notice Reward asset from game logic (authorized games only)
    function rewardAsset(address player, uint256 assetId, uint256 amount)
        external
        onlyAuthorizedGame
    {
        Asset storage asset = assets[assetId];
        require(asset.minted + amount <= asset.maxSupply, "Exceeds max supply");
        asset.minted += amount;
        _mint(player, assetId, amount, "");
        emit AssetMinted(player, assetId, amount);
    }

    /// @notice Authorize a game contract to mint/reward
    function authorizeGame(address gameContract) external onlyOwner {
        authorizedGames[gameContract] = true;
    }

    /// @notice Get all asset IDs for a game
    function getGameAssets(string calldata gameId) external view returns (uint256[] memory) {
        return games[gameId].assetIds;
    }

    function setBaseURI(string calldata newURI) external onlyOwner {
        baseURI = newURI;
    }

    function uri(uint256 tokenId) public view override returns (string memory) {
        return string(abi.encodePacked(baseURI, tokenId.toString(), ".json"));
    }

    function withdraw() external onlyOwner {
        payable(owner()).transfer(address(this).balance);
    }
}
