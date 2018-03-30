from kirby.rom.rom import *
from kirby.utils.reader import *
from kirby.compression import hal
import asyncio
import pytest
import random
import os


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


def byterange(max):
    for i in range(max):
        yield (i & 0xFF).to_bytes(1, "big")


async def atest_compression():
    assert await hal.compress(bytes(1025)) == b"\xE7\xFF\x00\0\0\xFF"
    assert await hal.compress(b"\0\x01" * 1024) == b"\xEB\xFF\x00\x01\xFF"
    assert await hal.compress(b"".join(list(byterange(1024)))) == b"\xEF\xFF\x00\xFF"
    assert await hal.compress(b"\0\0\x01\x01\0\0\x01\x01") == b"\x21\0\x21\x01\x83\0\0\xff"
    assert await hal.compress(b"\0\x01\x02\x03\x03\x02\x01\0") == b"\x63\0\xC3\0\x03\xff"
    assert await hal.compress(b"\0\x01\x02\x03\0\x80\x40\xC0") == b"\x63\0\xA3\0\0\xff"
    assert await hal.compress(b"\0\0\x01\x01\x02\0\0\x01\x01\x03") == b"\x21\0\x21\x01\0\x02\x83\0\0\0\x03\xff"


def test_decompression():
    asyncio.get_event_loop().run_until_complete(atest_decompression())


def test_compression():
    asyncio.get_event_loop().run_until_complete(atest_compression())


if __name__ == "__main__":
    test_compression()
