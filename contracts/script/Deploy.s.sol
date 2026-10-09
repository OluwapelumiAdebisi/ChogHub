// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console2} from "forge-std/Script.sol";
import {MockChog} from "../src/MockChog.sol";
import {MockChogToken} from "../src/MockChogToken.sol";
import {ChogVendor} from "../src/ChogVendor.sol";
import {ChogRegistry} from "../src/ChogRegistry.sol";

/// Testnet: deploys all four contracts and stocks the vendor.
///   forge script script/Deploy.s.sol --rpc-url monad_testnet --broadcast --private-key $DEPLOYER_KEY
/// Env: ATTESTER_ADDRESS (backend signer). Optional: CHOG_PER_MON (default 1000).
/// Mainnet: set REGISTRY_ONLY=true to deploy just ChogRegistry.
contract Deploy is Script {
    function run() external {
        address attester = vm.envAddress("ATTESTER_ADDRESS");
        bool registryOnly = vm.envOr("REGISTRY_ONLY", false);
        uint256 rate = vm.envOr("CHOG_PER_MON", uint256(1_000)) * 1 ether;

        vm.startBroadcast();
        address deployer = msg.sender;

        ChogRegistry registry = new ChogRegistry(deployer, attester);
        console2.log("CHOG_REGISTRY_ADDRESS=", address(registry));

        if (!registryOnly) {
            MockChog nft = new MockChog();
            MockChogToken token = new MockChogToken(deployer);
            ChogVendor vendor = new ChogVendor(token, rate);
            token.transfer(address(vendor), 500_000_000 ether);
            nft.mint(); // the deployer gets Chog #1 for the demo

            console2.log("CHOG_NFT_ADDRESS=", address(nft));
            console2.log("CHOG_TOKEN_ADDRESS=", address(token));
            console2.log("CHOG_VENDOR_ADDRESS=", address(vendor));
        }
        vm.stopBroadcast();
    }
}
