from kirby.rom.rom import *
from kirby.utils.reader import *
from kirby.compression import hal
import asyncio
import pytest
import random


async def atest_decompression():
    async with ROM("tests/data/test.bin") as f:
        assert len(await hal.decompress(f)) == 19
    async with ROM(ABytesIO()) as f:
        await f.write(0, b"\0\xFF\xA0\0\0" + b"\xEB\xFF\0\0" * 100000)
        with pytest.raises(ValueError):
            await hal.decompress(f, 0)
    async with ROM(ABytesIO()) as f:
        await f.write(0, b"\xFE\xFF\xFF")
        with pytest.raises(ValueError):
            await hal.decompress(f, 0)


async def atest_compression():
    print(await hal.compress(b"\x00\x01" * 10000))


def test_decompression():
    asyncio.get_event_loop().run_until_complete(atest_decompression())


def test_compression():
    asyncio.get_event_loop().run_until_complete(atest_compression())


if __name__ == "__main__":
    test_compression()