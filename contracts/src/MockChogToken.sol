// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/// @title MockChogToken — testnet stand-in for the CHOG token (1B supply, like the real one)
contract MockChogToken is ERC20 {
    constructor(address treasury) ERC20("Mock Chog", "CHOG") {
        _mint(treasury, 1_000_000_000 ether);
    }
}
