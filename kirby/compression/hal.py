import asyncio
import threading


async def decompress(rom, addr=None):
    if addr is None:
        addr = await rom.tell()
    data = b""

    while True:
        input = await rom.read(addr, "b")
        addr += 1
        if input == 0xFF:
            break
        if (input & 0xE0) == 0xE0:
            command = (input >> 2) & 0x7
            length = (((input & 3) << 8) | (await rom.read(addr, "b"))) + 1
            addr += 1
        else:
            command = input >> 5
            length = (input & 31) + 1

        if ((command == 2) and (len(data) + 2 * length > 65535)
                ) or (len(data) + length > 65535):
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
        elif command == 4:
            pos = await rom.read(addr, "h", "big")
            addr += 2
            t = data[pos:pos + length]
            assert len(t) == length
            data += t
        elif command == 5:
            pos = await rom.read(addr, "h", "big")
            addr += 2

            def bitrotate(x):
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
            t = data[pos:pos + length]
            assert len(t) == length
            data += b''.join([bitrotate(x).to_bytes(1, "big") for x in t])
        elif command == 6:
            pos = await rom.read(addr, "h", "big")
            addr += 2
            assert pos - length >= 0
            t = data[pos:pos - length:-1]
            assert len(t) == length
            data += t
        else:
            raise ValueError("Unknown command")

    return data


async def compress(data, fast=False):
    event = asyncio.Event()
    loop = asyncio.get_event_loop()
    outdata = b""

    def worker():
        nonlocal outdata, data, fast, event, loop
        uncompressed_data = b""
        pos = 0

        def find_rle8():
            match = data[pos]
            longest = 1
            for i in range(1025):
                if data[pos + i] != match:
                    break
                longest = i + 1

            return (1, longest, match)

        def find_rle16():
            match = data[pos:pos + 2]
            longest = 1
            for i in range(1025):
                if data[pos + i * 2:pos + i * 2 + 2] != match:
                    break
                longest = i + 1

            return (2, longest * 2, match)

        def find_rleinc():
            match = data[pos]
            longest = 1
            for i in range(1025):
                if data[pos + i] != (match + i) & 0xFF:
                    break
                longest = i + 1

            return (3, longest, match)

        def find_backref():
            def find_backref_at(off):
                maxlen = min(pos - off, 1025)
                for i in range(maxlen):
                    if data[off + i] != data[pos + i]:
                        return (i, off)
                    return (None, off)

            return_list = []
            for i in range(pos):
                if data[i] == data[pos]:
                    return_list.append(find_backref_at(i))
            if return_list == []:
                return None

            return (4, *max(return_list, key=lambda item: item[0]))

        def find_rot_backref():
            def bitrotate(x):
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

            def find_backref_at(off):
                maxlen = min(pos - off, 1025)
                for i in range(maxlen):
                    if bitrotate(data[off + i]) != data[pos + i]:
                        return (i, off)

                return (None, off)

            return_list = []
            for i in range(pos):
                if bitrotate(data[i]) == data[pos]:
                    return_list.append(find_backref_at(i))
            if return_list == []:
                return None

            return (5, *max(return_list, key=lambda item: item[0]))

        def find_backbackref():
            def find_backref_at(off):
                maxlen = min(off, 1025)
                for i in range(maxlen):
                    if data[off - i] != data[pos + i]:
                        return (i, off)

                return (None, off)

            return_list = []
            for i in range(pos):
                if data[i] == data[pos]:
                    return_list.append(find_backref_at(i))
            if return_list == []:
                return None

            return (6, *max(return_list, key=lambda item: item[0]))

        def make_header(command, length):
            if length > 32:
                return (0xE000 + (command << 10) + length).to_bytes(2, "big")
            return ((command << 5) + length).to_bytes(1, "big")

        while pos < len(data):
            print(pos, len(data))
            result_list = [
                find_rle8(),
                find_rle16(),
                find_rleinc(),
                find_backref()]
            if not fast:
                result_list += [find_rot_backref(), find_backbackref()]
            result_list = [x for x in result_list if x is not None]
            candidate_kind, uncompressed_size, data = max(
                result_list, key=lambda item: item[1])

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
                    outdata += data.to_bytes(1, "big")
                elif candidate_kind > 3:
                    outdata += data.to_bytes(2, "big")
                else:
                    outdata += data

                pos += uncompressed_size
            else:
                uncompressed_data += data[pos:pos + 1]
                pos += 1
                if len(uncompressed_data) == 1025:
                    outdata += make_header(0, 1024)
                    outdata += uncompressed_data
                    uncompressed_data = b""

        if uncompressed_data != b"":
            outdata += make_header(0, len(uncompressed_data) - 1)
            outdata += uncompressed_data
            uncompressed_data = b""

        outdata += b"\xFF"
        loop.call_soon_threadsafe(event.set)

    t = threading.Thread(target=worker)
    t.start()
    await event.wait()
    t.join()
    return outdata
