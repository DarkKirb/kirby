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
            length = (((input & 3) << 8) | (await rom.read(addr, "b")))+1
            addr += 1
        else:
            command = input >> 5
            length = (input & 31) + 1


        if ((command == 2) and (len(data)+2*length > 65535)) or (len(data)+length > 65535):
            raise ValueError("Compressed data is too big")

        if command == 0:
            data += await rom.read(addr, length)
            addr += length
        elif command == 1:
            data += (await rom.read(addr, 1))*length
            addr += 1
        elif command == 2:
            data += (await rom.read(addr, 2))*length
            addr += 2
        elif command == 3:
            n = await rom.read(addr, 1)
            addr += 1
            for x in range(length):
                data += (n[0] + x).to_bytes(1, "little")
        elif command == 4:
            pos = await rom.read(addr, "h", "big")
            addr += 2
            t = data[pos:pos+length]
            assert len(t) == length
            data += t
        elif command == 5:
            pos = await rom.read(addr, "h", "big")
            addr += 2
            def bitrotate(x):
                y=0
                if  x& 0x80:
                    y|=0x01
                if  x& 0x40:
                    y|=0x02
                if  x& 0x20:
                    y|=0x04
                if  x& 0x10:
                    y|=0x08
                if  x& 0x08:
                    y|=0x10
                if  x& 0x04:
                    y|=0x20
                if  x& 0x02:
                    y|=0x40
                if  x& 0x01:
                    y|=0x80
                return y
            t = data[pos:pos+length]
            assert len(t) == length
            data += b''.join([bitrotate(x).to_bytes(1, "big") for x in t])
        elif command == 6:
            pos = await rom.read(addr, "h", "big")
            addr += 2
            assert pos - length >= 0
            t = data[pos:pos-length:-1]
            assert len(t) == length
            data += t
        else:
            raise ValueError("Unknown command")

    return data
