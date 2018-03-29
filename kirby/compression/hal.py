"""Hal compression functions"""
import asyncio
import threading


def _bitrotate(x):
    y = 0
    if x & 0x80:
        y |= 0x01
    if x & 0x40:
        y |= 0x02
    if x & 0x20:
        y |= 0x04
    if x & 0x10:
        y |= 0x08
    if x & 0x08:
        y |= 0x10
    if x & 0x04:
        y |= 0x20
    if x & 0x02:
        y |= 0x40
    if x & 0x01:
        y |= 0x80
    return y


async def _parse_input(rom, addr):
    input = await rom.read(addr, "b")
    addr += 1
    if input == 0xFF:
        return addr, None, None
    if (input & 0xE0) == 0xE0:
        command = (input >> 2) & 7
        length = (((input & 3) << 8) | (await rom.read(addr, "b"))) + 1
        addr += 1
    else:
        command = input >> 5
        length = (input & 31) + 1
    return addr, command, length


async def _parse_backref(command, length, data, rom, addr):
    pos = await rom.read(addr, "h", "big")
    addr += 2
    if command == 6:
        assert pos - length >= 0
        t = data[pos:pos - length:-1]
    else:
        t = data[pos:pos + length]
    assert len(t) == length
    if command == 5:
        t = b''.join(_bitrotate(x).to_bytes(1, "big") for x in t)

    return addr, t


async def decompress(rom, addr=None):
    """Decompress data from rom into a bytes object.
    If the input is malformed (uncompressed data is bigger than 64KiB),
    an exception is raised"""
    if addr is None:
        addr = await rom.tell()
    data = b""

    while True:
        addr, command, length = await _parse_input(rom, addr)
        if command is None:
            break

        if ((command == 2) and (len(data) + 2 * length > 65535)) \
                or (len(data) + length > 65535):
            raise ValueError("Compressed data is too big")

        if command == 0:
            data += await rom.read(addr, length)
            addr += length
        elif command == 1:
            data += (await rom.read(addr, 1)) * length
            addr += 1
        elif command == 2:
            data += (await rom.read(addr, 2)) * length
            addr += 2
        elif command == 3:
            n = await rom.read(addr, 1)
            addr += 1
            for x in range(length):
                data += (n[0] + x).to_bytes(1, "little")
        elif command <= 6:
            addr, t = await _parse_backref(command, length, data, rom, addr)
            print(data, t)
            data += t
        else:
            raise ValueError("Unknown command")

    return data


def _find_rle8(data, pos):
    match = data[pos]
    longest = 1
    maxlen = min(len(data) - pos, 1024)
    for i in range(maxlen):
        if data[pos + i] != match:
            break
        longest = i + 1
    return (1, longest, match)


def _find_rle16(data, pos):
    match = data[pos:pos + 2]
    longest = 1
    maxlen = min(len(data) - pos, 1024)
    for i in range(maxlen):
        if data[pos + i * 2:pos + i * 2 + 2] != match:
            break
        longest = i + 1
    return (2, longest * 2, match)


def _find_rleinc(data, pos):
    match = data[pos]
    longest = 1
    maxlen = min(len(data) - pos, 1024)
    for i in range(maxlen):
        if data[pos + i] != (match + i) & 0xFF:
            break
        longest = i + 1

    return (3, longest, match)


def _find_backref_at(data, pos, off, kind):
    if kind != 2:
        maxlen = min(pos - off, 1024)
    else:
        maxlen = min(off, 1024)
    if kind == 0:
        def nop(x):
            return x
        match_fun = nop
    else:
        match_fun = _bitrotate

    for i in range(maxlen):
        j = i if kind != 2 else -i
        if match_fun(data[off + j] != data[pos + i]):
            return (i, off)
        return (None, off)


def _find_backref(data, pos):
    return_list = []
    for i in range(pos):
        if data[i] == data[pos]:
            return_list.append(_find_backref_at(data, pos, i, 0))
    return_list = [x for x in return_list if x is not None]
    return_list = [x for x in return_list if x[0] is not None]
    if return_list == []:
        return None

    return (4, *max(return_list, key=lambda item: item[0]))


def _find_rot_backref(data, pos):
    return_list = []
    for i in range(pos):
        if _bitrotate(data[i]) == data[pos]:
            return_list.append(_find_backref_at(data, pos, i, 1))
    return_list = [x for x in return_list if x is not None]
    return_list = [x for x in return_list if x[0] is not None]
    if return_list == []:
        return None

    return (5, *max(return_list, key=lambda item: item[0]))


def _find_backbackref(data, pos):
    return_list = []
    for i in range(pos):
        if data[i] == data[pos]:
            return_list.append(_find_backref_at(data, pos, i, 2))
    return_list = [x for x in return_list if x is not None]
    return_list = [x for x in return_list if x[0] is not None]
    if return_list == []:
        return None

    return (6, *max(return_list, key=lambda item: item[0]))


def _worker(outdata, data, fast, event, loop):
    uncompressed_data = b""
    pos = 0

    def make_header(command, length):
        if length > 32:
            return (0xE000 + (command << 10) + length).to_bytes(2, "big")
        return ((command << 5) + length).to_bytes(1, "big")

    while pos < len(data):
        print(pos, len(data))
        result_list = [
            _find_rle8(data, pos),
            _find_rle16(data, pos),
            _find_rleinc(data, pos),
            _find_backref(data, pos)]
        if not fast:
            result_list += [_find_rot_backref(data, pos),
                            _find_backbackref(data, pos)]
        result_list = [x for x in result_list if x is not None]
        candidate_kind, uncompressed_size, contents = max(
                                                      result_list,
                                                      key=lambda item: item[1])

        if ((candidate_kind in [1, 3]) and uncompressed_size > 3) or (
                (candidate_kind not in [1, 3]) and uncompressed_size > 4):
            # use compressed thing
            # first, clear out any uncompressed data
            if uncompressed_data != b"":
                outdata += make_header(0, len(uncompressed_data) - 1)
                outdata += uncompressed_data
                uncompressed_data = b""

            if candidate_kind == 2:
                outdata += make_header(2, (uncompressed_size // 2) - 1)
            else:
                outdata += make_header(candidate_kind, uncompressed_size - 1)

            if candidate_kind in [1, 3]:
                outdata += contents.to_bytes(1, "big")
            elif candidate_kind > 3:
                outdata += contents.to_bytes(2, "big")
            else:
                outdata += contents

            pos += uncompressed_size
        else:
            uncompressed_data += data[pos:pos + 1]
            pos += 1
            if len(uncompressed_data) == 1024:
                outdata += make_header(0, 1024)
                outdata += uncompressed_data
                uncompressed_data = b""

    if uncompressed_data != b"":
        outdata += make_header(0, len(uncompressed_data) - 1)
        outdata += uncompressed_data
        uncompressed_data = b""

    outdata += b"\xFF"
    loop.call_soon_threadsafe(event.set)


async def compress(data, fast=False, debug=False):
    """Compresses data (bytes-like) into a bytes object"""
    event = asyncio.Event()
    loop = asyncio.get_event_loop()
    outdata = bytearray()

    if not debug:
        t = threading.Thread(target=_worker, args=[outdata, data,
                                                   fast, event, loop])
        t.start()
        await event.wait()
        t.join()
    else:
        _worker(outdata, data, fast, event, loop)
        await event.wait()
    return outdata
