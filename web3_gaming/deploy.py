"""
Deployment script for .OG Gaming Platform contracts.

Usage:
    python deploy.py --network sepolia --private-key 0x...

Deploys:
    1. GameToken (OGT) - ERC-20 in-game currency
    2. GameAssetNFT - ERC-1155 game items
    3. OGDomainRegistry - .og domain NFTs with gamer profiles
"""

import argparse
import json
import os

from web3 import Web3
from eth_account import Account
from solcx import compile_standard, install_solc


def compile_contracts():
    """Compile all Solidity contracts."""
    install_solc("0.8.20")

    contracts_dir = os.path.join(os.path.dirname(__file__), "contracts")
    sources = {}
    for f in os.listdir(contracts_dir):
        if f.endswith(".sol"):
            with open(os.path.join(contracts_dir, f)) as fh:
                sources[f] = {"content": fh.read()}

    compiled = compile_standard(
        {
            "language": "Solidity",
            "sources": sources,
            "settings": {
                "outputSelection": {"*": {"*": ["abi", "evm.bytecode"]}},
                "optimizer": {"enabled": True, "runs": 200},
            },
        },
        solc_version="0.8.20",
        allow_paths=[contracts_dir],
    )

    # Save ABIs
    abis_dir = os.path.join(os.path.dirname(__file__), "abis")
    os.makedirs(abis_dir, exist_ok=True)

    result = {}
    for source_name, contracts in compiled["contracts"].items():
        for contract_name, contract_data in contracts.items():
            abi = contract_data["abi"]
            bytecode = contract_data["evm"]["bytecode"]["object"]
            result[contract_name] = {"abi": abi, "bytecode": bytecode}
            with open(os.path.join(abis_dir, f"{contract_name}.json"), "w") as f:
                json.dump(abi, f, indent=2)

    return result


def deploy(rpc_url: str, private_key: str):
    """Deploy all contracts."""
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    account = Account.from_key(private_key)
    print(f"Deployer: {account.address}")
    print(f"Balance: {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} ETH")

    contracts = compile_contracts()
    deployed = {}

    for name in ["GameToken", "GameAssetNFT", "OGDomainRegistry"]:
        print(f"\nDeploying {name}...")
        data = contracts[name]
        contract = w3.eth.contract(abi=data["abi"], bytecode=data["bytecode"])

        if name == "GameAssetNFT":
            constructor_tx = contract.constructor("https://api.oggaming.xyz/assets/").build_transaction({
                "from": account.address,
                "nonce": w3.eth.get_transaction_count(account.address),
            })
        else:
            constructor_tx = contract.constructor().build_transaction({
                "from": account.address,
                "nonce": w3.eth.get_transaction_count(account.address),
            })

        signed = w3.eth.account.sign_transaction(constructor_tx, account.key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        deployed[name] = receipt.contractAddress
        print(f"  {name}: {receipt.contractAddress}")

    # Save deployment addresses
    deploy_path = os.path.join(os.path.dirname(__file__), "deployments.json")
    with open(deploy_path, "w") as f:
        json.dump(deployed, f, indent=2)

    print(f"\nDeployment complete! Addresses saved to {deploy_path}")
    return deployed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy .OG Gaming contracts")
    parser.add_argument("--rpc-url", required=True, help="RPC endpoint URL")
    parser.add_argument("--private-key", required=True, help="Deployer private key")
    args = parser.parse_args()
    deploy(args.rpc_url, args.private_key)
