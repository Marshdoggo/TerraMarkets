// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol";

contract TerraMarkets {
    struct Market {
        string question;
        uint256 endTime;
        address creator;
        uint256 totalYes;
        uint256 totalNo;
        bool resolved;
        bool outcomeYes;
    }

    mapping(uint256 => Market) public markets;
    mapping(uint256 => mapping(address => uint256)) public userYesBets;
    mapping(uint256 => mapping(address => uint256)) public userNoBets;
    uint256 public marketCount;
    address public admin;

    event MarketCreated(uint256 indexed marketId, string question, uint256 endTime, address creator);
    event BetPlaced(uint256 indexed marketId, address indexed user, uint256 amount, bool betYes);
    event MarketResolved(uint256 indexed marketId, bool outcomeYes);
    event WinningsClaimed(uint256 indexed marketId, address indexed user, uint256 amount);

    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin can perform this action");
        _;
    }

    modifier marketOpen(uint256 marketId) {
        require(block.timestamp < markets[marketId].endTime, "Market is closed");
        _;
    }

    constructor() {
        admin = msg.sender;
    }

    function createMarket(string memory question, uint256 duration) external {
        uint256 marketId = marketCount++;
        markets[marketId] = Market(question, block.timestamp + duration, msg.sender, 0, 0, false, false);
        emit MarketCreated(marketId, question, block.timestamp + duration, msg.sender);
    }

    function placeBet(uint256 marketId, bool betYes) external payable marketOpen(marketId) {
        require(msg.value > 0, "Must place a bet");
        if (betYes) {
            userYesBets[marketId][msg.sender] += msg.value;
            markets[marketId].totalYes += msg.value;
        } else {
            userNoBets[marketId][msg.sender] += msg.value;
            markets[marketId].totalNo += msg.value;
        }
        emit BetPlaced(marketId, msg.sender, msg.value, betYes);
    }

    function resolveMarket(uint256 marketId, bool outcomeYes) external onlyAdmin {
        require(block.timestamp >= markets[marketId].endTime, "Market not yet ended");
        require(!markets[marketId].resolved, "Market already resolved");

        markets[marketId].resolved = true;
        markets[marketId].outcomeYes = outcomeYes;
        emit MarketResolved(marketId, outcomeYes);
    }

    function claimWinnings(uint256 marketId) external {
        require(markets[marketId].resolved, "Market not yet resolved");
        uint256 winnings;

        if (markets[marketId].outcomeYes && userYesBets[marketId][msg.sender] > 0) {
            winnings = (userYesBets[marketId][msg.sender] * (markets[marketId].totalYes + markets[marketId].totalNo)) / markets[marketId].totalYes;
        } else if (!markets[marketId].outcomeYes && userNoBets[marketId][msg.sender] > 0) {
            winnings = (userNoBets[marketId][msg.sender] * (markets[marketId].totalYes + markets[marketId].totalNo)) / markets[marketId].totalNo;
        }

        require(winnings > 0, "No winnings to claim");
        userYesBets[marketId][msg.sender] = 0;
        userNoBets[marketId][msg.sender] = 0;
        payable(msg.sender).transfer(winnings);
        emit WinningsClaimed(marketId, msg.sender, winnings);
    }
}
