from ..utils.reader import Reader


class ROM(Reader):
    def resolve(self, addr):
        return addr

    async def read(self, addr, size, endian="little"):
        if isinstance(size, int):
            await self.seek(self.resolve(addr))
            return await super().read(size)
        if size == "s":  # string
            s = await self.read(addr, "i", endian)
            return (await super().read(s)).decode()
        if size == "b":  # byte
            return (await self.read(addr, 1))[0]
        if size == "h":  # halfword
            return int.from_bytes(await self.read(addr, 2), endian)
        if size == "a":  # 24-bit address
            return int.from_bytes(await self.read(addr, 3), endian)
        if size == "i":  # int
            return int.from_bytes(await self.read(addr, 4), endian)
        raise RuntimeError("Unsupported read format!")

    async def write(self, addr, data, size=None, endian="little"):
        if isinstance(data, bytes):
            await self.seek(self.resolve(addr))
            await super().write(data)
        elif isinstance(data, str):
            encoded = data.encode()
            await self.write(addr, len(encoded), "i", endian)
            await super().write(encoded)
        elif size == "b" or (size is None and data < 2**8):
            await self.write(addr, data.to_bytes(1, endian))
        elif size == "h" or (size is None and data < 2**16):
            await self.write(addr, data.to_bytes(2, endian))
        elif size == "a" or (size is None and data < 2**24):
            await self.write(addr, data.to_bytes(3, endian))
        elif size == "i" or (size is None and data < 2**32):
            await self.write(addr, data.to_bytes(4, endian))
        else:
            raise RuntimeError("Unsupported write format!")

    async def memset(self, addr, to, data):
        await self.write(addr, data * (to - addr))

    async def find_new_loc(self, length, start=None, end=None):
        if start is None:
            start = 0
        if end is None:
            x = await self.tell()
            await self.seek(0, 2)
            end = await self.tell()
            await self.seek(x)
        ostart = start
        start = self.resolve(start)
        end = self.resolve(end)
        data = await self.read(start, end - start)

        pos = 0
        while pos + length <= len(data):
            if data[pos] not in [0, 255]:
                pos += 1
                continue
            if data[pos + length - 1] not in [0, 255]:
                pos += length
                continue
            found = True
            for j in range(pos, pos + length):
                if data[j] not in [0, 255]:
                    found = False
                    print(data[j], j)
                    pos = j
                    break
            if found:
                return ostart + pos

        raise ValueError("Not enough space found!")

    async def relocate(self, data, start=None, end=None):
        pos = await self.find_new_loc(len(data), start, end)
        await self.write(pos, data)
        return pos


class GBROM(ROM):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bank = 1

    def resolve(self, addr):
        if addr & 0xFFFF >= 0x4000:
            raise ValueError("Outside of ROM!")
        bank = addr >> 16
        off = addr & 0xFFFF
        if off < 0x2000:
            return off
        if addr & 0xFF0000 == 0:
            return self.bank * 0x2000 + off - 0x2000
        self.bank = bank
        return self.bank * 0x2000 + off - 0x2000

    async def bankswitch(self, bank):
        self.bank = bank

    async def bank_count(self):
        x = await self.tell()
        await self.seek(0, 2)
        end = await self.tell()
        await self.seek(x)
        return end // 0x2000

    async def find_new_loc(self, length, start=None, end=None):
        if start is None:
            start_bank = 0
        else:
            start_bank = start // 0x2000
        if end is None:
            end_bank = await self.bank_count()
        else:
            end_bank = end // 0x2000
        for i in range(max(start_bank, 1), end_bank):
            try:
                return await super().find_new_loc(length,
                                                  i * 0x10000 + 0x2000,
                                                  i * 0x10000 + 0x4000)
            except ValueError:
                pass
        if start_bank != 0:
            raise ValueError("Not enough space found!")
        return await super().find_new_loc(length, 0, 0x2000)
