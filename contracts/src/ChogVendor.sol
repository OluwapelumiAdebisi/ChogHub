// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title ChogVendor — fixed-rate MON -> CHOG sale for the testnet demo
/// @notice The agent prepares a `buy(minOut)` call; the user signs it in their wallet.
contract ChogVendor is Ownable {
    using SafeERC20 for IERC20;

    IERC20 public immutable chog;
    /// @notice CHOG (18 decimals) received per 1 MON (18 decimals).
    uint256 public chogPerMon;

    event Bought(address indexed buyer, uint256 monIn, uint256 chogOut);
    event RateChanged(uint256 chogPerMon);

    error ZeroValue();
    error Slippage(uint256 out, uint256 minOut);
    error InsufficientInventory();

    constructor(IERC20 chog_, uint256 chogPerMon_) Ownable(msg.sender) {
        chog = chog_;
        chogPerMon = chogPerMon_;
    }

    /// @notice MON (wei) needed to buy `chogAmount` CHOG (wei), rounded up.
    function quote(uint256 chogAmount) public view returns (uint256 monIn) {
        monIn = (chogAmount * 1 ether + chogPerMon - 1) / chogPerMon;
    }

    function buy(uint256 minOut) external payable returns (uint256 out) {
        if (msg.value == 0) revert ZeroValue();
        out = (msg.value * chogPerMon) / 1 ether;
        if (out < minOut) revert Slippage(out, minOut);
        if (chog.balanceOf(address(this)) < out) revert InsufficientInventory();
        chog.safeTransfer(msg.sender, out);
        emit Bought(msg.sender, msg.value, out);
    }

    function setRate(uint256 chogPerMon_) external onlyOwner {
        chogPerMon = chogPerMon_;
        emit RateChanged(chogPerMon_);
    }

    function withdraw(address payable to) external onlyOwner {
        (bool ok,) = to.call{value: address(this).balance}("");
        require(ok, "withdraw failed");
    }
}
