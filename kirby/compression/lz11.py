"""Compression module for Nintendo's LZSS format"""
import argparse
import asyncio
import sys
from ..rom.rom import ROM
from ..utils.reader import ABytesIO


def to_bits(byte):
    return reversed((byte & 1,
                     (byte >> 1) & 1,
                     (byte >> 2) & 1,
                     (byte >> 3) & 1,
                     (byte >> 4) & 1,
                     (byte >> 5) & 1,
                     (byte >> 6) & 1,
                     (byte >> 7)))


async def decompress(rom, addr, overlay=False):
    # Read the header
    header = await rom.read(addr, "i")
    addr += 4
    reserved = header & 15
    compressed_type = (header >> 4) & 15
    assert compressed_type == 1
    decomp_size = header >> 8
    if decomp_size == 0:
        decomp_size = await rom.read(addr, "i")
        addr += 4
    outdata = b""
    try:
        while len(outdata) < decomp_size:
            # read flag byte
            bits = to_bits(await rom.read(addr, "b"))
            addr += 1
            for bit in bits:
                if not bit:  # handle uncompressed data
                    outdata += await rom.read(addr, 1)
                    addr += 1
                else:
                    lenmsb = await rom.read(addr, "b")
                    lsb = await rom.read(addr + 1, "b")
                    addr += 2
                    length = lenmsb >> 4
                    disp = (lenmsb & 15 << 8) + lsb
                    if reserved == 0:
                        length += 3
                        if overlay:
                            disp -= 2
                    elif length > 1:
                        length += 1
                    elif length == 0:
                        length = lenmsb & 15 << 4
                        length += lsb >> 4
                        length += 0x11
                        msb = await rom.read(addr, "b")
                        addr += 1
                        disp = (lenmsb & 15 << 8) + msb
                    else:
                        assert length == 1
                        length = lenmsb & 15 << 12
                        length += lsb << 4
                        byte1, byte2 = await rom.read(addr, 2)
                        addr += 2
                        length += byte1 >> 4
                        disp = (byte1 & 15 << 8) + byte2
                        length += 0x111
                    start = len(outdata) - disp - 1
                    end = start + length
                    if end > len(outdata):  # slow byte-per-byte copy
                        for i in range(start, end):
                            outdata += outdata[i:i + 1]
                    else:
                        outdata += outdata[start:end]
    except (ValueError, IndexError):
        pass
    return outdata[:decomp_size]


class UncompressedByte:
    def __init__(self, data, pos):
        self.data = data[pos:pos + 1]

    def __int__(self):
        return 0

    def __bytes__(self):
        return bytes(self.data)


class CompressedBytes:
    def __init__(self, data, pos, overlay):
        self.data = data
        self.pos = pos
        self.doff = 3 if overlay else 1
        self.overlay = overlay

    def __aiter__(self):    # I forgot that python3.5 doesn't support async
                            # generators, so this is my solution for now
        self.iterator = self.find_matches()
        return self

    async def __anext__(self):
        try:
            return next(self.iterator)
        except StopIteration as e:
            raise StopAsyncIteration from e

    def find_matches(self):
        for i in range(max(0, self.pos - 2**24 - self.doff),
                       self.pos - self.doff + 1):
            if self.data[i] == self.data[self.pos]:
                # found a match, find longest possible match
                for j in range(min(len(self.data) - i,
                                   len(self.data) - self.pos,
                                   0x11 if self.overlay else 0x10111)):
                    if self.data[i + j] != self.data[self.pos + j]:
                        yield (i, j)
                        break
                if self.data[i:i + j + 1] == self.data[self.pos:]:
                    yield (i, j + 1)

    async def init(self):
        # find longest possible match
        longest_pos = 0
        longest_len = -1
        async for pos, length in self:
            if length > longest_len:
                longest_pos, longest_len = pos, length

        self.off = self.pos - longest_pos - self.doff
        self.len = longest_len

    def __int__(self):
        return 1

    def __bytes__(self):
        if self.len < 17:
            lenmsb = (self.off >> 8) + ((self.len - 1) << 4)
            return (lenmsb.to_bytes(1, "big") +
                    (self.off & 0xFF).to_bytes(1, "big"))
        elif self.len < 0x111:
            length = self.len - 0x11
            firstbyte = length >> 4
            secondbyte = (self.off >> 8) + ((length & 15) << 4)
            return (firstbyte.to_bytes(1, "big") +
                    secondbyte.to_bytes(1, "big") +
                    (self.off & 0xFF).to_bytes(1, "big"))
        elif self.len < 0x10111:
            length = self.len - 0x111
            firstbyte = (length >> 12) + 0x10
            secondbyte = (length >> 8) & 0xFF
            thirdbyte = (self.off >> 8) + ((length & 15) << 4)
            return (firstbyte.to_bytes(1, "big") +
                    secondbyte.to_bytes(1, "big") +
                    thirdbyte.to_bytes(1, "big") +
                    (self.off & 0xFF).to_bytes(1, "big"))
        raise ValueError("Length too big")  # pragma: no cover


async def compress(data, force_large=False, overlay=False):
    # Step 1: read in data into list
    if overlay:
        assert not force_large
        assert len(data) < 2**24
    matches = []
    off = 0
    while off < len(data):
        repetition = CompressedBytes(data, off, overlay)
        await repetition.init()
        if repetition.len < 3:
            matches.append(UncompressedByte(data, off))
            off += 1
        else:
            matches.append(repetition)
            off += repetition.len

    # Step 2: writing all of the data into a buffer
    outdata = b"\x10" if overlay else b"\x11"
    if len(data) >= 2**24 or force_large:
        outdata += b"\0\0\0" + len(data).to_bytes(4, "little")
    else:
        outdata += len(data).to_bytes(3, "little")
    databuf = b""
    cmd_byte = 0
    for i, match in enumerate(matches):
        cmd_byte <<= 1
        cmd_byte += int(match)
        databuf += bytes(match)
        if i % 8 == 7:
            outdata += cmd_byte.to_bytes(1, "big")
            outdata += databuf
            databuf = b""
            cmd_byte = 0

    # Shift the cmd byte if necessary
    if i % 8 == 7:
        return outdata + b"\xFF"
    else:
        cmd_byte <<= 7 - i % 8
        outdata += cmd_byte.to_bytes(1, "big")
        outdata += databuf
        return outdata + b"\xFF"


async def decompress_overlay(rom):
    await rom.seek(-8, 2)
    header_pos = await rom.tell()
    end_delta = await rom.read(header_pos, "i")
    start_delta = await rom.read(header_pos + 4, "i")
    filelen = header_pos + 8
    padding = end_delta >> 0x18
    end_delta &= 0xFFFFFF
    decompressed_size = start_delta + end_delta
    data = bytearray()
    print(filelen, end_delta)
    data.extend(await rom.read(filelen - end_delta, end_delta - padding))
    data.reverse()
    async with ROM(ABytesIO(data)) as f:
        x = bytearray(await decompress(f, 0, overlay=True))
        x.reverse()
        return (await rom.read(0, filelen - end_delta) +
                x)


async def compress_overlay(data):
    revdata = bytearray(data)
    revdata.reverse()
    compdata = await compress(revdata, overlay=True)
    revcompdata = bytearray(compdata)
    revcompdata.reverse()
    revcompdata = revcompdata[1:]
    start_delta = 0
    end_delta = len(revcompdata) + 8
    end_delta += 8 << 0x18
    return (revcompdata +
            end_delta.to_bytes(4, "little") +
            start_delta.to_bytes(4, "little"))


def decompress_main():
    parser = argparse.ArgumentParser(
        description="Decompress a file using LZ10/LZ11 compression"
    )
    parser.add_argument("file", metavar="file", type=str,
                        help="File to compress")
    parser.add_argument("--output", "-o", dest="outfile", metavar="file",
                        type=str, help="File to save to (default: stdout)",
                        nargs="?")
    parser.add_argument("--allow-tty", dest="tty", action="store_const",
                        default=False, const=True, help="Allow output on TTY")
    parser.add_argument("--overlay", dest="overlay", action="store_const",
                        default=False, const=True,
                        help="Use overlay version of LZ10")
    args = parser.parse_args()
    with open(args.file, "rb") as f:
        data = f.read()

    if args.outfile is None:
        outfile = sys.stdout.buffer
        if sys.stdout.isatty() and not args.tty:
            raise ValueError("Refusing to output binary data to tty")
    else:
        outfile = open(args.outfile, "wb")

    event_loop = asyncio.get_event_loop()
    romfile = ROM(ABytesIO(data))
    event_loop.run_until_complete(romfile.__aenter__())
    if args.overlay:
        coro = decompress_overlay(romfile)
    else:
        coro = decompress(romfile, 0)
    outfile.write(event_loop.run_until_complete(coro))
    event_loop.run_until_complete(romfile.__aexit__(None, None, None))
    outfile.flush()
    if args.outfile is not None:
        outfile.close()


def compress_main():
    parser = argparse.ArgumentParser(
        description="Compress a file using LZ10/LZ11 compression"
    )
    parser.add_argument("file", metavar="file", type=str,
                        help="File to compress")
    parser.add_argument("--output", "-o", dest="outfile", metavar="file",
                        type=str, help="File to save to (default: stdout)",
                        nargs="?")
    parser.add_argument("--allow-tty", dest="tty", action="store_const",
                        default=False, const=True, help="Allow output on TTY")
    parser.add_argument("--overlay", dest="overlay", action="store_const",
                        default=False, const=True,
                        help="Use overlay version of LZ10")
    args = parser.parse_args()
    with open(args.file, "rb") as f:
        data = f.read()

    if args.outfile is None:
        outfile = sys.stdout.buffer
        if sys.stdout.isatty() and not args.tty:
            raise ValueError("Refusing to output binary data on tty")
    else:
        outfile = open(args.outfile, "wb")

    event_loop = asyncio.get_event_loop()
    if args.overlay:
        coro = compress_overlay(data)
    else:
        coro = compress(data)
    outfile.write(event_loop.run_until_complete(coro))
    outfile.flush()
    if args.outfile is not None:
        outfile.close()
