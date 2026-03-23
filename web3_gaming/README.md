# .OG Gaming - Web3 Gaming Platform with Domain Integration

A Web3 gaming platform that uses **.og** domains as universal gaming identities, with cross-game NFT assets and an in-game token economy.

## Architecture

```
web3_gaming/
├── contracts/           # Solidity smart contracts
│   ├── OGDomainRegistry.sol  # .og domain NFT registry + gamer profiles
│   ├── GameAssetNFT.sol      # ERC-1155 cross-game items
│   └── GameToken.sol         # OGT ERC-20 in-game currency
├── sdk/                 # Python SDK
│   ├── og_domains.py         # Domain registration & resolution
│   ├── game_assets.py        # NFT asset management
│   ├── game_token.py         # Token operations & staking
│   └── gaming_platform.py    # Unified high-level API
├── frontend/            # Web application
│   └── index.html            # Single-page gaming dashboard
├── tests/               # Unit tests
├── deploy.py            # Contract deployment script
└── hardhat.config.js    # Hardhat configuration
```

## Quick Start

### 1. Install Dependencies

```bash
pip install web3 eth-account py-solc-x
npm install --save-dev hardhat @nomicfoundation/hardhat-toolbox @openzeppelin/contracts
```

### 2. Deploy Contracts

```bash
python web3_gaming/deploy.py --rpc-url https://sepolia.infura.io/v3/YOUR_KEY --private-key 0xYOUR_KEY
```

### 3. Use the SDK

```python
from web3_gaming.sdk import GamingPlatform

platform = GamingPlatform(
    rpc_url="https://sepolia.infura.io/v3/YOUR_KEY",
    domain_contract="0x...",
    asset_contract="0x...",
    token_contract="0x...",
    private_key="0x...",
)

# Register your .og gaming identity
platform.register_identity("epicgamer", duration_years=1)

# Get player profile
profile = platform.get_player_profile("epicgamer")

# Record game results (updates on-chain stats)
platform.record_game_result("epicgamer", "battle-arena", won=True, xp=250)
```

### 4. Launch Frontend

Open `web3_gaming/frontend/index.html` in a browser. Connect MetaMask to interact with deployed contracts.

## .OG Domain Features

- **Register** `.og` domains as ERC-721 NFTs (min 3 chars)
- **Gamer profiles** with level, XP, win rate tracked on-chain
- **Reverse resolution** - look up a `.og` name from any address
- **Text records** - store avatar URLs, bios, social links
- **Auto-leveling** - every 1000 XP = 1 level up

## Game Asset System

- **ERC-1155 multi-token** - weapons, armor, skins, consumables, achievements, land
- **Cross-game compatible** - assets can be used across registered games
- **Rarity tiers** - Common, Uncommon, Rare, Epic, Legendary
- **Game developer SDK** - register games and create custom assets

## OGT Token

- **1 billion max supply** with deflationary mechanics
- **Staking** - stake OGT for yield rewards
- **Play-to-earn** - authorized games mint reward tokens
- **Governance** - token holders vote on platform decisions
