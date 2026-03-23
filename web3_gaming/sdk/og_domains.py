"""Client for interacting with the OG Domain Registry contract."""

import json
import os
from web3 import Web3
from eth_account import Account


class OGDomainClient:
    """Manage .og domain registrations, records, and gamer profiles."""

    def __init__(self, rpc_url: str, contract_address: str, private_key: str = None):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.account = Account.from_key(private_key) if private_key else None

        abi_path = os.path.join(os.path.dirname(__file__), "..", "abis", "OGDomainRegistry.json")
        if os.path.exists(abi_path):
            with open(abi_path) as f:
                abi = json.load(f)
        else:
            abi = self._default_abi()

        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address), abi=abi
        )

    def register(self, name: str, duration_years: int = 1) -> dict:
        """Register a .og domain."""
        price = self.contract.functions.pricePerYear().call()
        total_cost = price * duration_years

        tx = self.contract.functions.register(name, duration_years).build_transaction({
            "from": self.account.address,
            "value": total_cost,
            "nonce": self.w3.eth.get_transaction_count(self.account.address),
            "gas": 500_000,
        })
        return self._send_tx(tx)

    def renew(self, name: str, additional_years: int = 1) -> dict:
        """Renew a .og domain."""
        price = self.contract.functions.pricePerYear().call()
        total_cost = price * additional_years

        tx = self.contract.functions.renew(name, additional_years).build_transaction({
            "from": self.account.address,
            "value": total_cost,
            "nonce": self.w3.eth.get_transaction_count(self.account.address),
            "gas": 200_000,
        })
        return self._send_tx(tx)

    def resolve(self, name: str) -> str:
        """Resolve a .og domain to an address."""
        return self.contract.functions.resolve(name).call()

    def reverse_lookup(self, address: str) -> str:
        """Get the .og domain for an address."""
        return self.contract.functions.reverseLookup(
            Web3.to_checksum_address(address)
        ).call()

    def set_record(self, name: str, key: str, value: str) -> dict:
        """Set a text record on a domain."""
        tx = self.contract.functions.setRecord(name, key, value).build_transaction({
            "from": self.account.address,
            "nonce": self.w3.eth.get_transaction_count(self.account.address),
            "gas": 100_000,
        })
        return self._send_tx(tx)

    def get_record(self, name: str, key: str) -> str:
        """Get a text record from a domain."""
        return self.contract.functions.getRecord(name, key).call()

    def get_gamer_profile(self, name: str) -> dict:
        """Get the gamer profile for a domain."""
        result = self.contract.functions.getGamerProfile(name).call()
        return {
            "display_name": result[0],
            "level": result[1],
            "xp": result[2],
            "games_played": result[3],
            "wins": result[4],
        }

    def update_gamer_profile(
        self, name: str, display_name: str = "", xp_gained: int = 0,
        games_played: int = 0, wins: int = 0
    ) -> dict:
        """Update gamer profile stats."""
        tx = self.contract.functions.updateGamerProfile(
            name, display_name, xp_gained, games_played, wins
        ).build_transaction({
            "from": self.account.address,
            "nonce": self.w3.eth.get_transaction_count(self.account.address),
            "gas": 200_000,
        })
        return self._send_tx(tx)

    def set_primary_domain(self, name: str) -> dict:
        """Set a domain as primary for reverse resolution."""
        tx = self.contract.functions.setPrimaryDomain(name).build_transaction({
            "from": self.account.address,
            "nonce": self.w3.eth.get_transaction_count(self.account.address),
            "gas": 100_000,
        })
        return self._send_tx(tx)

    def get_expiry(self, name: str) -> int:
        """Get domain expiry timestamp."""
        return self.contract.functions.getExpiry(name).call()

    def _send_tx(self, tx: dict) -> dict:
        signed = self.w3.eth.account.sign_transaction(tx, self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return {"tx_hash": tx_hash.hex(), "status": receipt["status"]}

    @staticmethod
    def _default_abi():
        """Minimal ABI for when compiled artifacts aren't available."""
        return [
            {"inputs": [], "name": "pricePerYear", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"type": "string"}, {"type": "uint256"}], "name": "register", "outputs": [], "stateMutability": "payable", "type": "function"},
            {"inputs": [{"type": "string"}, {"type": "uint256"}], "name": "renew", "outputs": [], "stateMutability": "payable", "type": "function"},
            {"inputs": [{"type": "string"}], "name": "resolve", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"type": "address"}], "name": "reverseLookup", "outputs": [{"type": "string"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"type": "string"}, {"type": "string"}, {"type": "string"}], "name": "setRecord", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"type": "string"}, {"type": "string"}], "name": "getRecord", "outputs": [{"type": "string"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"type": "string"}], "name": "getGamerProfile", "outputs": [{"type": "string"}, {"type": "uint256"}, {"type": "uint256"}, {"type": "uint256"}, {"type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"type": "string"}, {"type": "string"}, {"type": "uint256"}, {"type": "uint256"}, {"type": "uint256"}], "name": "updateGamerProfile", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"type": "string"}], "name": "setPrimaryDomain", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"type": "string"}], "name": "getExpiry", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
        ]
