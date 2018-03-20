from ..utils.reader import *

class ROM(Reader):
    def resolve(self, addr):
        return addr

    async def read(self, addr, size, endian="little"):
        if isinstance(size, int):
            await self.seek(resolve(addr))
            return await super().read(size)
        if size == "s": #string
            s = await self.read(addr, "i", endian)
            return (await super().read(s)).decode()
        if size == "b": #byte
            return (await self.read(addr, 1))[0]
        if size == "h": #halfword
            return int.from_bytes(await self.read(addr, 2), endian)
        if size == "a": #24-bit address
            return int.from_bytes(await self.read(addr, 3), endian)
        if size == "i": #int
            return int.from_bytes(await self.read(addr, 4), endian)

    async def write(self, addr, data, size=None, endian="little"):
        if isinstance(data, bytes):
            await self.seek(resolve(addr))
            await super().write(addr)
        elif isinstance(data, str):
            await self.write(addr, len(data), "i", endian)
            await self.write(await self.tell(), data.encode())
        elif size == "b" or data < 2**8:
            await self.write(addr, data.to_bytes(1, endian))
        elif size == "w" or data < 2**16:
            await self.write(addr, data.to_bytes(2, endian))
        elif size == "a" or data < 2**24:
            await self.write(addr, data.to_bytes(3, endian))
        elif size == "i" or data < 2**32:
            await self.write(addr, data.to_bytes(4, endian))


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
