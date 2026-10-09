// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {ERC721Enumerable} from "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Strings} from "@openzeppelin/contracts/utils/Strings.sol";
import {Base64} from "@openzeppelin/contracts/utils/Base64.sol";

/// @title MockChog — testnet stand-in for the Chog NFT collection
/// @notice Free mint (max 3 per wallet), traits derived on-chain at mint time,
///         fully on-chain SVG metadata so the demo needs no IPFS.
contract MockChog is ERC721Enumerable, Ownable {
    using Strings for uint256;

    uint256 public constant MAX_PER_WALLET = 3;
    uint256 public constant MAX_SUPPLY = 10_000;

    struct Traits {
        uint8 hat;        // index into HATS
        uint8 mood;       // index into MOODS
        uint8 background; // index into BACKGROUNDS
    }

    string[5] private HATS = ["None", "Pirate Hat", "Crown", "Beanie", "Party Hat"];
    string[4] private MOODS = ["Chaotic", "Sleepy", "Hyped", "Mischievous"];
    string[4] private BACKGROUNDS = ["Purple", "Night", "Mint", "Sunset"];
    string[4] private BG_HEX = ["#836EF9", "#1E1B4B", "#A7F3D0", "#FDBA74"];

    uint256 private _nextId = 1;
    mapping(uint256 => Traits) private _traits;
    mapping(address => uint256) public mintedBy;

    event ChogMinted(address indexed to, uint256 indexed tokenId, Traits traits);

    error MintLimitReached();
    error SoldOut();

    constructor() ERC721("Mock Chog", "MCHOG") Ownable(msg.sender) {}

    function mint() external returns (uint256 tokenId) {
        if (mintedBy[msg.sender] >= MAX_PER_WALLET) revert MintLimitReached();
        tokenId = _mintTo(msg.sender);
        mintedBy[msg.sender] += 1;
    }

    /// @notice Owner can airdrop Chogs (e.g. to judges' wallets).
    function airdrop(address to) external onlyOwner returns (uint256) {
        return _mintTo(to);
    }

    function traitsOf(uint256 tokenId) external view returns (string memory hat, string memory mood, string memory background) {
        _requireOwned(tokenId);
        Traits memory t = _traits[tokenId];
        return (HATS[t.hat], MOODS[t.mood], BACKGROUNDS[t.background]);
    }

    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        _requireOwned(tokenId);
        Traits memory t = _traits[tokenId];
        string memory name = string.concat("Chog #", tokenId.toString());
        string memory json = string.concat(
            '{"name":"', name,
            '","description":"A Mock Chog for the ChogHub testnet demo.","image":"data:image/svg+xml;base64,',
            Base64.encode(bytes(_svg(tokenId, t))),
            '","attributes":[{"trait_type":"Hat","value":"', HATS[t.hat],
            '"},{"trait_type":"Mood","value":"', MOODS[t.mood],
            '"},{"trait_type":"Background","value":"', BACKGROUNDS[t.background], '"}]}'
        );
        return string.concat("data:application/json;base64,", Base64.encode(bytes(json)));
    }

    function _mintTo(address to) internal returns (uint256 tokenId) {
        if (_nextId > MAX_SUPPLY) revert SoldOut();
        tokenId = _nextId++;
        uint256 seed = uint256(keccak256(abi.encodePacked(block.prevrandao, to, tokenId)));
        Traits memory t = Traits({
            hat: uint8(seed % HATS.length),
            mood: uint8((seed >> 8) % MOODS.length),
            background: uint8((seed >> 16) % BACKGROUNDS.length)
        });
        _traits[tokenId] = t;
        _safeMint(to, tokenId);
        emit ChogMinted(to, tokenId, t);
    }

    function _svg(uint256 tokenId, Traits memory t) internal view returns (string memory) {
        return string.concat(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">',
            '<rect width="200" height="200" fill="', BG_HEX[t.background], '"/>',
            '<ellipse cx="100" cy="120" rx="62" ry="52" fill="#5B3FD6"/>',
            '<circle cx="76" cy="104" r="14" fill="#fff"/><circle cx="124" cy="104" r="14" fill="#fff"/>',
            '<circle cx="79" cy="106" r="6" fill="#111"/><circle cx="121" cy="106" r="6" fill="#111"/>',
            '<path d="M80 140 Q100 152 120 140" stroke="#111" stroke-width="4" fill="none"/>',
            t.hat == 0 ? "" : string.concat('<rect x="66" y="52" width="68" height="18" rx="6" fill="#111"/>'),
            '<text x="100" y="190" font-family="monospace" font-size="14" text-anchor="middle" fill="#fff">#',
            tokenId.toString(), "</text></svg>"
        );
    }
}
