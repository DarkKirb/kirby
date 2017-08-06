WARNING: The game mixes endians. Please always take note of the endianess of a specific thing
## Offsets
All those offsets are for the international version of the game.

- Metadata table: `0x38b1`
- Level tilesets: `0x2070`
- Tile table: `0x20A2` This links the tiles from the tileset to 2x2 tiles stored in VRAM

## VRAM

- VRAM base `0x8800` (Tiles >= `0x80` are start at `0x8800`, all others at `0x9000`
Tiles used for all rooms: (Tiles `0x7c-0x7F`)
- `0x97C0-0x97CF`: All black (FF)
- `0x97D0-0x97DF`: Dark grey (00, FF repeated)
- `0x97E0-0x97EF`: Light grey (FF, 00 repeated)
- `0x97F0-0x97FF`: White (00 repeated)

## Compression
Programs that can compress/decompress: [Exhal](https://github.com/devinacker/exhal), [Lunar Compress](http://fusoya.eludevisibility.org/lc/). Exhal should be pretty self-explanatory.


## Map metadata pointer table
It is at `0x38B1` length 10 bytes of __little endian__ 16 bit pointers into the map metadata table. The pointers point to the first room in each level.

## Map metadata table
| Field | Length | Endianess | Meaning          |
|-------|--------|-----------|------------------|
| 0x00  | 1      |           | Bank of Map data |
| 0x01  | 2      | **BIG**   | Offset in Bank   |
| 0x03  | 1      |           | Width of room    |
| 0x04  | 1      |           | Height of room   |
| 0x05  | 3      |           | Unknown          |

## Tileset table
I have no idea how to determine the tileset. I hardcoded them. Just use the level ID, except in level 4, where I use the room ID -1 for rooms 1…4
Tilesets are compressed
| Field | Length | Endianess  | Meaning                       |
|-------|--------|------------|-------------------------------|
| 0x0   | 2      | **little** | Offset in this tileset's bank |
| 0x2   | 1      |            | Bank of tileset               |
| 0x3   | 2      | **BIG**    | location of tileset (in VRAM) |
| 0x5   | 1      |            | Bank of tile order information|
| 0x6   | 2      | **BIG**    | Tile order information        |

## Tile order information
The tiles used by the map data are 16x16px in size, while the PPU can only manage 8x8 tiles. This list contains 4 entries for each of the 256 tiles, namely tile numbers for UL, UR, DL, DR in this order.

This data is compressed

## Map format
Maps are stored in a 2D array of 2x2-block numbers. The height and width of this array are specified in the map metadata table.

This data is compressed.

## Unknowns:

- Where the enemies are stored
- Where the tileset ID is stored
