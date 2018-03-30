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
