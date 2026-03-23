"""Client for interacting with the GameAssetNFT contract."""

import json
import os
from web3 import Web3
from eth_account import Account


class GameAssetClient:
    """Manage ERC-1155 gaming assets: weapons, skins, achievements."""

    ASSET_TYPES = {
        "WEAPON": 0, "ARMOR": 1, "SKIN": 2,
        "CONSUMABLE": 3, "ACHIEVEMENT": 4, "LAND": 5,
    }

    def __init__(self, rpc_url: str, contract_address: str, private_key: str = None):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.account = Account.from_key(private_key) if private_key else None

        abi_path = os.path.join(os.path.dirname(__file__), "..", "abis", "GameAssetNFT.json")
        if os.path.exists(abi_path):
            with open(abi_path) as f:
                abi = json.load(f)
        else:
            abi = self._default_abi()

        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address), abi=abi
        )

    def register_game(self, game_id: str, name: str) -> dict:
        """Register a new game on the platform."""
        tx = self.contract.functions.registerGame(game_id, name).build_transaction({
            "from": self.account.address,
            "nonce": self.w3.eth.get_transaction_count(self.account.address),
            "gas": 300_000,
        })
        return self._send_tx(tx)

    def create_asset(
        self, name: str, asset_type: str, rarity: int, power: int,
        max_supply: int, price_wei: int, tradeable: bool, game_id: str
    ) -> dict:
        """Create a new asset type for a game."""
        type_id = self.ASSET_TYPES.get(asset_type.upper(), 0)
        tx = self.contract.functions.createAsset(
            name, type_id, rarity, power, max_supply, price_wei, tradeable, game_id
        ).build_transaction({
            "from": self.account.address,
            "nonce": self.w3.eth.get_transaction_count(self.account.address),
            "gas": 400_000,
        })
        return self._send_tx(tx)

    def mint_asset(self, to: str, asset_id: int, amount: int = 1) -> dict:
        """Mint assets to a player."""
        asset = self.contract.functions.assets(asset_id).call()
        price = asset[6] * amount  # price field

        tx = self.contract.functions.mintAsset(
            Web3.to_checksum_address(to), asset_id, amount
        ).build_transaction({
            "from": self.account.address,
            "value": price,
            "nonce": self.w3.eth.get_transaction_count(self.account.address),
            "gas": 200_000,
        })
        return self._send_tx(tx)

    def equip_asset(self, game_id: str, asset_id: int) -> dict:
        """Equip an asset in a game."""
        tx = self.contract.functions.equipAsset(game_id, asset_id).build_transaction({
            "from": self.account.address,
            "nonce": self.w3.eth.get_transaction_count(self.account.address),
            "gas": 150_000,
        })
        return self._send_tx(tx)

    def get_equipped(self, player: str, game_id: str) -> list:
        """Get equipped assets for a player in a game."""
        return self.contract.functions.getEquippedAssets(
            Web3.to_checksum_address(player), game_id
        ).call()

    def get_balance(self, player: str, asset_id: int) -> int:
        """Get a player's balance for an asset."""
        return self.contract.functions.balanceOf(
            Web3.to_checksum_address(player), asset_id
        ).call()

    def get_game_assets(self, game_id: str) -> list:
        """Get all asset IDs for a game."""
        return self.contract.functions.getGameAssets(game_id).call()

    def get_asset_info(self, asset_id: int) -> dict:
        """Get asset metadata."""
        result = self.contract.functions.assets(asset_id).call()
        type_names = {v: k for k, v in self.ASSET_TYPES.items()}
        return {
            "name": result[0],
            "asset_type": type_names.get(result[1], "UNKNOWN"),
            "rarity": result[2],
            "power": result[3],
            "max_supply": result[4],
            "minted": result[5],
            "price": result[6],
            "tradeable": result[7],
            "game_id": result[8],
        }

    def _send_tx(self, tx: dict) -> dict:
        signed = self.w3.eth.account.sign_transaction(tx, self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return {"tx_hash": tx_hash.hex(), "status": receipt["status"]}

    @staticmethod
    def _default_abi():
        return [
            {"inputs": [{"type": "string"}, {"type": "string"}], "name": "registerGame", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"type": "string"}, {"type": "uint8"}, {"type": "uint256"}, {"type": "uint256"}, {"type": "uint256"}, {"type": "uint256"}, {"type": "bool"}, {"type": "string"}], "name": "createAsset", "outputs": [{"type": "uint256"}], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"type": "address"}, {"type": "uint256"}, {"type": "uint256"}], "name": "mintAsset", "outputs": [], "stateMutability": "payable", "type": "function"},
            {"inputs": [{"type": "string"}, {"type": "uint256"}], "name": "equipAsset", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"type": "address"}, {"type": "string"}], "name": "getEquippedAssets", "outputs": [{"type": "uint256[]"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"type": "address"}, {"type": "uint256"}], "name": "balanceOf", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"type": "string"}], "name": "getGameAssets", "outputs": [{"type": "uint256[]"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"type": "uint256"}], "name": "assets", "outputs": [{"type": "string"}, {"type": "uint8"}, {"type": "uint256"}, {"type": "uint256"}, {"type": "uint256"}, {"type": "uint256"}, {"type": "uint256"}, {"type": "bool"}, {"type": "string"}], "stateMutability": "view", "type": "function"},
        ]
