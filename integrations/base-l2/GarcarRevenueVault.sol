// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// GARCAR Revenue Vault — Base L2 (Chain ID: 8453)
// Deploy to Base Mainnet via: npx hardhat deploy --network base
// Audit via: smart-contract-auditor-ai before production deploy

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

contract GarcarRevenueVault is Ownable, ReentrancyGuard {
    
    // Revenue event tracking
    struct RevenueEvent {
        address payer;
        uint256 amount;
        string source;      // "shopify" | "stripe" | "huggingface" | "direct"
        string productId;
        uint256 timestamp;
    }
    
    // Treasury address (Garrettc123 controlled wallet)
    address public treasury;
    
    // Accepted USDC on Base
    IERC20 public constant USDC = IERC20(0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913);
    
    // Revenue events log
    RevenueEvent[] public revenueEvents;
    
    // Total settled revenue by source
    mapping(string => uint256) public revenueBySource;
    uint256 public totalRevenue;
    
    // Events
    event RevenuePaid(address indexed payer, uint256 amount, string source, string productId);
    event TreasuryWithdrawal(address indexed to, uint256 amount);
    event TreasuryUpdated(address indexed oldTreasury, address indexed newTreasury);
    
    constructor(address _treasury) Ownable(msg.sender) {
        require(_treasury != address(0), "Treasury cannot be zero address");
        treasury = _treasury;
    }
    
    // Accept USDC payment for a product/service
    function payRevenue(
        uint256 amount,
        string calldata source,
        string calldata productId
    ) external nonReentrant {
        require(amount > 0, "Amount must be greater than 0");
        require(USDC.transferFrom(msg.sender, address(this), amount), "USDC transfer failed");
        
        revenueEvents.push(RevenueEvent({
            payer: msg.sender,
            amount: amount,
            source: source,
            productId: productId,
            timestamp: block.timestamp
        }));
        
        revenueBySource[source] += amount;
        totalRevenue += amount;
        
        emit RevenuePaid(msg.sender, amount, source, productId);
    }
    
    // Accept native ETH payments
    receive() external payable {
        revenueEvents.push(RevenueEvent({
            payer: msg.sender,
            amount: msg.value,
            source: "direct_eth",
            productId: "",
            timestamp: block.timestamp
        }));
        totalRevenue += msg.value;
        emit RevenuePaid(msg.sender, msg.value, "direct_eth", "");
    }
    
    // Owner: withdraw all USDC to treasury
    function withdrawUSDC() external onlyOwner nonReentrant {
        uint256 balance = USDC.balanceOf(address(this));
        require(balance > 0, "No USDC to withdraw");
        require(USDC.transfer(treasury, balance), "USDC withdrawal failed");
        emit TreasuryWithdrawal(treasury, balance);
    }
    
    // Owner: withdraw all ETH to treasury
    function withdrawETH() external onlyOwner nonReentrant {
        uint256 balance = address(this).balance;
        require(balance > 0, "No ETH to withdraw");
        (bool success, ) = treasury.call{value: balance}("");
        require(success, "ETH withdrawal failed");
        emit TreasuryWithdrawal(treasury, balance);
    }
    
    // Update treasury address
    function setTreasury(address _treasury) external onlyOwner {
        require(_treasury != address(0), "Treasury cannot be zero address");
        emit TreasuryUpdated(treasury, _treasury);
        treasury = _treasury;
    }
    
    // View: get all revenue events count
    function getRevenueEventCount() external view returns (uint256) {
        return revenueEvents.length;
    }
    
    // View: get revenue event by index
    function getRevenueEvent(uint256 index) external view returns (RevenueEvent memory) {
        require(index < revenueEvents.length, "Index out of bounds");
        return revenueEvents[index];
    }
}
