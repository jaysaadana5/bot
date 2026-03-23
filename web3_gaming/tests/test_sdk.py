"""Tests for the Web3 Gaming SDK (mock-based, no network required)."""

import unittest
from unittest.mock import MagicMock, patch


class TestOGDomainClient(unittest.TestCase):
    """Test OG Domain client methods."""

    @patch("web3_gaming.sdk.og_domains.Web3")
    @patch("web3_gaming.sdk.og_domains.Account")
    def test_get_gamer_profile_parses_response(self, mock_account, mock_web3):
        mock_w3 = MagicMock()
        mock_web3.return_value = mock_w3
        mock_web3.HTTPProvider.return_value = MagicMock()
        mock_web3.to_checksum_address.return_value = "0x" + "0" * 40

        from web3_gaming.sdk.og_domains import OGDomainClient

        client = OGDomainClient("http://localhost:8545", "0x" + "0" * 40)

        # Mock contract call
        client.contract.functions.getGamerProfile.return_value.call.return_value = (
            "TestPlayer", 5, 4500, 30, 18
        )

        profile = client.get_gamer_profile("testplayer")
        self.assertEqual(profile["display_name"], "TestPlayer")
        self.assertEqual(profile["level"], 5)
        self.assertEqual(profile["xp"], 4500)
        self.assertEqual(profile["games_played"], 30)
        self.assertEqual(profile["wins"], 18)


class TestGameAssetClient(unittest.TestCase):
    """Test Game Asset client methods."""

    @patch("web3_gaming.sdk.game_assets.Web3")
    @patch("web3_gaming.sdk.game_assets.Account")
    def test_asset_types_mapping(self, mock_account, mock_web3):
        mock_web3.return_value = MagicMock()
        mock_web3.HTTPProvider.return_value = MagicMock()
        mock_web3.to_checksum_address.return_value = "0x" + "0" * 40

        from web3_gaming.sdk.game_assets import GameAssetClient

        self.assertEqual(GameAssetClient.ASSET_TYPES["WEAPON"], 0)
        self.assertEqual(GameAssetClient.ASSET_TYPES["LEGENDARY"], None) if "LEGENDARY" in GameAssetClient.ASSET_TYPES else None
        self.assertEqual(GameAssetClient.ASSET_TYPES["LAND"], 5)


class TestGamingPlatform(unittest.TestCase):
    """Test the unified GamingPlatform interface."""

    @patch("web3_gaming.sdk.gaming_platform.GameTokenClient")
    @patch("web3_gaming.sdk.gaming_platform.GameAssetClient")
    @patch("web3_gaming.sdk.gaming_platform.OGDomainClient")
    def test_get_player_profile(self, mock_domain, mock_asset, mock_token):
        from web3_gaming.sdk.gaming_platform import GamingPlatform

        mock_domain_instance = mock_domain.return_value
        mock_token_instance = mock_token.return_value

        mock_domain_instance.get_gamer_profile.return_value = {
            "display_name": "Pro", "level": 10, "xp": 9500,
            "games_played": 100, "wins": 65,
        }
        mock_domain_instance.resolve.return_value = "0x" + "a" * 40
        mock_token_instance.balance_of.return_value = 5000
        mock_token_instance.staking_balance.return_value = 1000
        mock_token_instance.pending_reward.return_value = 50

        platform = GamingPlatform(
            "http://localhost:8545",
            "0x" + "1" * 40, "0x" + "2" * 40, "0x" + "3" * 40,
        )

        profile = platform.get_player_profile("pro")
        self.assertEqual(profile["level"], 10)
        self.assertEqual(profile["win_rate"], 65.0)
        self.assertEqual(profile["ogt_balance"], 5000)
        self.assertEqual(profile["domain"], "pro.og")


if __name__ == "__main__":
    unittest.main()
