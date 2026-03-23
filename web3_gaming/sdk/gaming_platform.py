"""
High-level Gaming Platform SDK that ties together .og domains,
game assets, and the OGT token into a unified interface.
"""

from .og_domains import OGDomainClient
from .game_assets import GameAssetClient
from .game_token import GameTokenClient


class GamingPlatform:
    """Unified Web3 gaming platform with .og domain integration.

    Usage:
        platform = GamingPlatform(
            rpc_url="https://rpc.example.com",
            domain_contract="0x...",
            asset_contract="0x...",
            token_contract="0x...",
            private_key="0x..."
        )

        # Register your .og gaming identity
        platform.register_identity("epicgamer", duration_years=2)

        # Get full player profile
        profile = platform.get_player_profile("epicgamer")

        # Record a game result
        platform.record_game_result("epicgamer", "battle-royale", won=True, xp=250)
    """

    def __init__(
        self, rpc_url: str, domain_contract: str,
        asset_contract: str, token_contract: str, private_key: str = None
    ):
        self.domains = OGDomainClient(rpc_url, domain_contract, private_key)
        self.assets = GameAssetClient(rpc_url, asset_contract, private_key)
        self.tokens = GameTokenClient(rpc_url, token_contract, private_key)
        self.rpc_url = rpc_url

    def register_identity(self, name: str, duration_years: int = 1) -> dict:
        """Register a .og domain as your gaming identity."""
        result = self.domains.register(name, duration_years)
        # Set default gaming records
        self.domains.set_record(name, "avatar", "default")
        self.domains.set_record(name, "bio", f"{name}.og - Web3 Gamer")
        return {
            "domain": f"{name}.og",
            "tx_hash": result["tx_hash"],
            "status": "registered",
        }

    def get_player_profile(self, name: str) -> dict:
        """Get comprehensive player profile from .og domain."""
        gamer = self.domains.get_gamer_profile(name)
        address = self.domains.resolve(name)
        token_balance = self.tokens.balance_of(address)
        staked = self.tokens.staking_balance(address)
        pending = self.tokens.pending_reward(address)

        return {
            "domain": f"{name}.og",
            "address": address,
            "display_name": gamer["display_name"],
            "level": gamer["level"],
            "xp": gamer["xp"],
            "games_played": gamer["games_played"],
            "wins": gamer["wins"],
            "win_rate": (gamer["wins"] / gamer["games_played"] * 100) if gamer["games_played"] > 0 else 0,
            "ogt_balance": token_balance,
            "ogt_staked": staked,
            "ogt_pending_reward": pending,
        }

    def record_game_result(
        self, name: str, game_id: str, won: bool = False, xp: int = 0
    ) -> dict:
        """Record a game result and update the player's .og profile."""
        wins = 1 if won else 0
        result = self.domains.update_gamer_profile(
            name, display_name="", xp_gained=xp, games_played=1, wins=wins
        )
        return {
            "domain": f"{name}.og",
            "game_id": game_id,
            "won": won,
            "xp_earned": xp,
            "tx_hash": result["tx_hash"],
        }

    def get_inventory(self, player_address: str, game_id: str) -> list:
        """Get a player's full inventory for a game."""
        asset_ids = self.assets.get_game_assets(game_id)
        inventory = []
        for asset_id in asset_ids:
            balance = self.assets.get_balance(player_address, asset_id)
            if balance > 0:
                info = self.assets.get_asset_info(asset_id)
                info["balance"] = balance
                inventory.append(info)
        return inventory

    def resolve_player(self, name_or_address: str) -> dict:
        """Resolve a player by .og name or address."""
        if name_or_address.endswith(".og"):
            name = name_or_address[:-3]
            address = self.domains.resolve(name)
            return {"name": name_or_address, "address": address}
        else:
            name = self.domains.reverse_lookup(name_or_address)
            return {"name": name, "address": name_or_address}
