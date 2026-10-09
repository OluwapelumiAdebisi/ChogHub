// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {MockChog} from "../src/MockChog.sol";
import {MockChogToken} from "../src/MockChogToken.sol";
import {ChogVendor} from "../src/ChogVendor.sol";
import {ChogRegistry} from "../src/ChogRegistry.sol";

contract ChogHubTest is Test {
    MockChog nft;
    MockChogToken token;
    ChogVendor vendor;
    ChogRegistry registry;

    address admin = address(this);
    address attester = makeAddr("attester");
    address alice = makeAddr("alice");
    address bob = makeAddr("bob");

    uint256 constant RATE = 1_000 ether; // 1 MON = 1,000 CHOG

    function setUp() public {
        nft = new MockChog();
        token = new MockChogToken(admin);
        vendor = new ChogVendor(token, RATE);
        token.transfer(address(vendor), 10_000_000 ether);
        registry = new ChogRegistry(admin, attester);
        vm.deal(alice, 100 ether);
    }

    // ---- MockChog ----

    function test_MintAndTraits() public {
        vm.prank(alice);
        uint256 id = nft.mint();
        assertEq(id, 1);
        assertEq(nft.ownerOf(1), alice);
        (string memory hat,,) = nft.traitsOf(1);
        assertTrue(bytes(hat).length > 0);
        assertTrue(bytes(nft.tokenURI(1)).length > 100);
    }

    function test_MintLimit() public {
        vm.startPrank(alice);
        nft.mint();
        nft.mint();
        nft.mint();
        vm.expectRevert(MockChog.MintLimitReached.selector);
        nft.mint();
        vm.stopPrank();
        assertEq(nft.balanceOf(alice), 3);
        assertEq(nft.tokenOfOwnerByIndex(alice, 2), 3);
    }

    // ---- ChogVendor ----

    function test_QuoteAndBuy() public {
        uint256 want = 10 ether; // 10 CHOG
        uint256 cost = vendor.quote(want);
        assertEq(cost, 0.01 ether);
        vm.prank(alice);
        uint256 out = vendor.buy{value: cost}(want);
        assertEq(out, want);
        assertEq(token.balanceOf(alice), want);
    }

    function test_BuySlippageReverts() public {
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(ChogVendor.Slippage.selector, 1 ether, 2 ether));
        vendor.buy{value: 0.001 ether}(2 ether);
    }

    // ---- ChogRegistry ----

    function test_OnlyAttesterWrites() public {
        vm.prank(alice);
        vm.expectRevert();
        registry.recordAchievement(address(nft), 1, "meme-warrior", ChogRegistry.Kind.Quest, bytes32(0));
    }

    function test_HistoryFollowsTheToken() public {
        vm.prank(alice);
        uint256 id = nft.mint();

        vm.startPrank(attester);
        registry.recordEvent(address(nft), id, "meme-wars", bytes32(0));
        registry.recordAchievement(address(nft), id, "meme-warrior", ChogRegistry.Kind.Quest, bytes32(0));
        vm.expectRevert(ChogRegistry.AlreadyRecorded.selector);
        registry.recordAchievement(address(nft), id, "meme-warrior", ChogRegistry.Kind.Quest, bytes32(0));
        vm.stopPrank();

        // Sell the Chog: stats are keyed by the token, so they stay with it.
        vm.prank(alice);
        nft.transferFrom(alice, bob, id);
        assertEq(nft.ownerOf(id), bob);

        ChogRegistry.Stats memory s = registry.statsOf(address(nft), id);
        assertEq(s.quests, 1);
        assertEq(s.events, 1);
        assertEq(registry.achievementsOf(address(nft), id).length, 1);
    }
}
