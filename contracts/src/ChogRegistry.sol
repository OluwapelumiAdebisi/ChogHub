// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title ChogRegistry — on-chain reputation that follows the NFT, not the wallet
/// @notice Keyed by (collection, tokenId), so it works with any ERC-721 and the
///         history moves with the token on every sale. Only the attester (the
///         ChogHub backend) writes; anyone reads.
contract ChogRegistry is AccessControl {
    bytes32 public constant ATTESTER_ROLE = keccak256("ATTESTER_ROLE");

    struct Stats {
        uint32 quests;       // achievements earned via quests
        uint32 events;       // events attended
        uint32 wins;         // competition wins
        uint32 contributions;
    }

    enum Kind { Quest, Win, Contribution }

    mapping(bytes32 => Stats) private _stats;
    mapping(bytes32 => bytes32[]) private _achievements;
    mapping(bytes32 => mapping(bytes32 => bool)) public hasAchievement;
    mapping(bytes32 => mapping(bytes32 => bool)) public attendedEvent;

    event AchievementRecorded(address indexed collection, uint256 indexed tokenId, bytes32 indexed achievementId, Kind kind, bytes32 ref);
    event EventAttended(address indexed collection, uint256 indexed tokenId, bytes32 indexed eventId, bytes32 ref);

    error AlreadyRecorded();

    constructor(address admin, address attester) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(ATTESTER_ROLE, attester);
    }

    function key(address collection, uint256 tokenId) public pure returns (bytes32) {
        return keccak256(abi.encode(collection, tokenId));
    }

    function recordAchievement(address collection, uint256 tokenId, bytes32 achievementId, Kind kind, bytes32 ref)
        external
        onlyRole(ATTESTER_ROLE)
    {
        bytes32 k = key(collection, tokenId);
        if (hasAchievement[k][achievementId]) revert AlreadyRecorded();
        hasAchievement[k][achievementId] = true;
        _achievements[k].push(achievementId);
        Stats storage s = _stats[k];
        if (kind == Kind.Quest) s.quests++;
        else if (kind == Kind.Win) s.wins++;
        else s.contributions++;
        emit AchievementRecorded(collection, tokenId, achievementId, kind, ref);
    }

    function recordEvent(address collection, uint256 tokenId, bytes32 eventId, bytes32 ref)
        external
        onlyRole(ATTESTER_ROLE)
    {
        bytes32 k = key(collection, tokenId);
        if (attendedEvent[k][eventId]) revert AlreadyRecorded();
        attendedEvent[k][eventId] = true;
        _stats[k].events++;
        emit EventAttended(collection, tokenId, eventId, ref);
    }

    function statsOf(address collection, uint256 tokenId) external view returns (Stats memory) {
        return _stats[key(collection, tokenId)];
    }

    function achievementsOf(address collection, uint256 tokenId) external view returns (bytes32[] memory) {
        return _achievements[key(collection, tokenId)];
    }
}
