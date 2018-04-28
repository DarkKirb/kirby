from kirby.rom.rom import ROM
from kirby.utils.reader import ABytesIO
from kirby.compression import hal, lz11
import asyncio
import pytest
import sys
import io
import os
import logging


logging.basicConfig(level=logging.DEBUG)


def isatty():
    return True


def async_test(f):
    def wrapper(*args, **kwargs):
        return asyncio.get_event_loop().run_until_complete(f(*args, **kwargs))
    if __name__ == "__main__":
        return f
    return wrapper


class ForceArgs:
    def __init__(self, *args):
        self.newargs = list(args)

    def __enter__(self):
        self.oldargs = sys.argv
        sys.argv = sys.argv[:1] + self.newargs

    def __exit__(self, *e):
        sys.argv = self.oldargs


class MockStdout:
    def __init__(self):
        self.buffer = io.BytesIO()

    def __enter__(self):
        self.origstdout = sys.stdout
        sys.stdout = self

    def __exit__(self, *e):
        sys.stdout = self.origstdout

    def isatty(self):
        return False

    def write(self, x):
        self.buffer.write(x.encode())
        return len(x)


@async_test
async def test_haldecompression():
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


@async_test
async def test_halcompression():
    assert await hal.compress(bytes(1025)) == b"\xE7\xFF\x00\0\0\xFF"
    assert await hal.compress(b"\0\x01" * 1024) == b"\xEB\xFF\x00\x01\xFF"
    assert await hal.compress(b"".join(list(byterange(1024)))) == b"\xEF\xFF\x00\xFF"
    assert await hal.compress(b"\0\0\x01\x01\0\0\x01\x01") == b"\x21\0\x21\x01\x83\0\0\xff"
    assert await hal.compress(b"\0\x01\x02\x03\x03\x02\x01\0") == b"\x63\0\xC3\0\x03\xff"
    assert await hal.compress(b"\0\x01\x02\x03\0\x80\x40\xC0") == b"\x63\0\xA3\0\0\xff"
    assert await hal.compress(b"\0\0\x01\x01\x02\0\0\x01\x01\x03") == b"\x21\0\x21\x01\0\x02\x83\0\0\0\x03\xff"
    assert await hal.compress(b"\0\0\x01\x01\x02\0\0\x01\x01\x03", fast=True) == b"\x21\0\x21\x01\0\x02\x83\0\0\0\x03\xff"


@async_test
async def test_halcompression_highentropy():
    with open("tests/data/highentropy.bin", "rb") as f:
        await hal.compress(f.read(), fast=True)


def test_halcompression_prog():
    sys.stdout.isatty = isatty
    with ForceArgs("tests/data/example.text"):
        with MockStdout():
            hal.compress_main()
            assert sys.stdout.buffer.getvalue() == b"\x63\x31\x67\x31\x63\x31\x00\x0a\xff"

    with ForceArgs("tests/data/example.text", "--progress"):
        with MockStdout():
            hal.compress_main()

    with pytest.raises(ValueError):
        with ForceArgs("tests/data/example.text"):
            hal.compress_main()

    with ForceArgs("tests/data/example.text", "-o", "testcmp.bin"):
        hal.compress_main()

    os.remove("testcmp.bin")


def test_haldecompression_prog():
    sys.stdout.isatty = isatty
    with ForceArgs("tests/data/example.text.cmp"):
        with MockStdout():
            hal.decompress_main()
            assert sys.stdout.buffer.getvalue() == b"1234123456781234\n"
    with pytest.raises(ValueError):
        with ForceArgs("tests/data/example.text.cmp"):
            hal.decompress_main()
    with ForceArgs("tests/data/example.text.cmp", "-o", "testcmp.bin"):
        hal.decompress_main()
    os.remove("testcmp.bin")


@async_test
async def test_lzdecompression():
    async with ROM("tests/data/lz11cmp.bin") as f:
        assert await lz11.decompress(f, 0) == b"This is an example text uiae nrtd uiae nrtd uiae nrtd"
    async with ROM("tests/data/lz11_large.bin") as f:
        assert await lz11.decompress(f, 0) == bytes(4370)


@async_test
async def test_lzcompression():
    with open("tests/data/lz11cmp.bin", "rb") as f:
        assert await lz11.compress(b"This is an example text uiae nrtd uiae nrtd uiae nrtd") == f.read()


@async_test
async def test_lzcompression_hard():
    assert await lz11.compress(bytes(2**16), True) == b"\x11\x00\x00\x00\x00\x00\x01\x00\x40\x00\x1f\xfe\xe0\x00\xff"


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait([test_haldecompression(),
                                          test_halcompression(),
                                          test_halcompression_highentropy(),
                                          test_lzdecompression(),
                                          test_lzcompression(),
                                          test_lzcompression_hard()]))
