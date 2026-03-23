"""Client for interacting with the OG Game Token (OGT) contract."""

import json
import os
from web3 import Web3
from eth_account import Account


class GameTokenClient:
    """Manage OGT token: transfers, staking, rewards."""

    def __init__(self, rpc_url: str, contract_address: str, private_key: str = None):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.account = Account.from_key(private_key) if private_key else None

        abi_path = os.path.join(os.path.dirname(__file__), "..", "abis", "GameToken.json")
        if os.path.exists(abi_path):
            with open(abi_path) as f:
                abi = json.load(f)
        else:
            abi = self._default_abi()

        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address), abi=abi
        )

    def balance_of(self, address: str) -> int:
        """Get OGT balance for an address."""
        return self.contract.functions.balanceOf(
            Web3.to_checksum_address(address)
        ).call()

    def transfer(self, to: str, amount: int) -> dict:
        """Transfer OGT tokens."""
        tx = self.contract.functions.transfer(
            Web3.to_checksum_address(to), amount
        ).build_transaction({
            "from": self.account.address,
            "nonce": self.w3.eth.get_transaction_count(self.account.address),
            "gas": 100_000,
        })
        return self._send_tx(tx)

    def stake(self, amount: int) -> dict:
        """Stake OGT tokens for rewards."""
        tx = self.contract.functions.stake(amount).build_transaction({
            "from": self.account.address,
            "nonce": self.w3.eth.get_transaction_count(self.account.address),
            "gas": 200_000,
        })
        return self._send_tx(tx)

    def unstake(self, amount: int) -> dict:
        """Unstake OGT tokens and claim rewards."""
        tx = self.contract.functions.unstake(amount).build_transaction({
            "from": self.account.address,
            "nonce": self.w3.eth.get_transaction_count(self.account.address),
            "gas": 200_000,
        })
        return self._send_tx(tx)

    def pending_reward(self, address: str) -> int:
        """Check pending staking rewards."""
        return self.contract.functions.pendingReward(
            Web3.to_checksum_address(address)
        ).call()

    def staking_balance(self, address: str) -> int:
        """Check staked balance."""
        return self.contract.functions.stakingBalance(
            Web3.to_checksum_address(address)
        ).call()

    def _send_tx(self, tx: dict) -> dict:
        signed = self.w3.eth.account.sign_transaction(tx, self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return {"tx_hash": tx_hash.hex(), "status": receipt["status"]}

    @staticmethod
    def _default_abi():
        return [
            {"inputs": [{"type": "address"}], "name": "balanceOf", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"type": "address"}, {"type": "uint256"}], "name": "transfer", "outputs": [{"type": "bool"}], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"type": "uint256"}], "name": "stake", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"type": "uint256"}], "name": "unstake", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"type": "address"}], "name": "pendingReward", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"type": "address"}], "name": "stakingBalance", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
        ]
