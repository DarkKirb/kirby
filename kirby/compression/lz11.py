"""Compression module for Nintendo's LZSS format"""


def to_bits(byte):
    return reversed((byte & 1,
                    (byte >> 1) & 1,
                    (byte >> 2) & 1,
                    (byte >> 3) & 1,
                    (byte >> 4) & 1,
                    (byte >> 5) & 1,
                    (byte >> 6) & 1,
                    (byte >> 7)))


async def decompress(rom, addr):
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
                    if reserved == 0 or length > 1:
                        disp = (lenmsb & 15 << 8) + lsb
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
