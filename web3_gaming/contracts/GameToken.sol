// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/// @title OG Game Token - In-game currency for the .og gaming ecosystem
contract GameToken is ERC20, Ownable {
    uint256 public constant MAX_SUPPLY = 1_000_000_000 * 1e18; // 1 billion tokens

    mapping(address => bool) public authorizedMinters; // game contracts
    mapping(address => uint256) public stakingBalance;
    mapping(address => uint256) public stakingTimestamp;

    uint256 public stakingRewardRate = 100; // basis points per year (1%)

    event Staked(address indexed user, uint256 amount);
    event Unstaked(address indexed user, uint256 amount, uint256 reward);
    event MinterAuthorized(address indexed minter);

    constructor() ERC20("OG Game Token", "OGT") Ownable(msg.sender) {
        // Mint initial supply: 30% team, 20% treasury, 50% rewards pool
        _mint(msg.sender, 300_000_000 * 1e18);       // team
        _mint(address(this), 200_000_000 * 1e18);     // treasury
        // 500M reserved for game rewards (minted by authorized games)
    }

    /// @notice Authorized game contracts can mint reward tokens
    function mintReward(address to, uint256 amount) external {
        require(authorizedMinters[msg.sender], "Not authorized");
        require(totalSupply() + amount <= MAX_SUPPLY, "Exceeds max supply");
        _mint(to, amount);
    }

    /// @notice Stake tokens to earn rewards
    function stake(uint256 amount) external {
        require(amount > 0, "Cannot stake 0");
        require(balanceOf(msg.sender) >= amount, "Insufficient balance");

        // Claim any pending rewards first
        if (stakingBalance[msg.sender] > 0) {
            _claimReward(msg.sender);
        }

        _transfer(msg.sender, address(this), amount);
        stakingBalance[msg.sender] += amount;
        stakingTimestamp[msg.sender] = block.timestamp;

        emit Staked(msg.sender, amount);
    }

    /// @notice Unstake tokens and claim rewards
    function unstake(uint256 amount) external {
        require(stakingBalance[msg.sender] >= amount, "Insufficient staked");

        uint256 reward = _calculateReward(msg.sender);
        stakingBalance[msg.sender] -= amount;

        _transfer(address(this), msg.sender, amount);
        if (reward > 0 && totalSupply() + reward <= MAX_SUPPLY) {
            _mint(msg.sender, reward);
        }

        stakingTimestamp[msg.sender] = block.timestamp;
        emit Unstaked(msg.sender, amount, reward);
    }

    /// @notice View pending staking reward
    function pendingReward(address user) external view returns (uint256) {
        return _calculateReward(user);
    }

    function _calculateReward(address user) internal view returns (uint256) {
        if (stakingBalance[user] == 0) return 0;
        uint256 duration = block.timestamp - stakingTimestamp[user];
        return (stakingBalance[user] * stakingRewardRate * duration) / (365 days * 10000);
    }

    function _claimReward(address user) internal {
        uint256 reward = _calculateReward(user);
        if (reward > 0 && totalSupply() + reward <= MAX_SUPPLY) {
            _mint(user, reward);
        }
        stakingTimestamp[user] = block.timestamp;
    }

    function authorizeMinter(address minter) external onlyOwner {
        authorizedMinters[minter] = true;
        emit MinterAuthorized(minter);
    }

    function setStakingRate(uint256 newRate) external onlyOwner {
        stakingRewardRate = newRate;
    }

    function withdrawTreasury(uint256 amount) external onlyOwner {
        _transfer(address(this), msg.sender, amount);
    }
}
