from kirby.utils.reader import *
import asyncio
import pytest


async def atest_reader():
    async with Reader(ABytesIO()) as f:
        assert (await f.write(b"uiae")) == 4
        assert (await f.seek(0)) == 0
        assert (await f.tell()) == 0
        assert (await f.read(1)) == b"u"
        assert (await f.read(10000)) == b"iae"
        assert (await f.read()) == b""
        await f.flush()
    async with Reader("tests/data/example.text") as f1:
        assert (await f1.read(4)) == b"1234"
        async with Reader(f1, 4, 12, True) as f2:
            assert (await f2.read()) == b"12345678"
            with pytest.raises(FileExtensionError):
                assert (await f2.write(b"1")) == 1
        assert (await f1.seek(1, 2)) == 16
        assert (await f1.seek(-4, 1)) == 12
        assert (await f1.read()) == b"1234\n"
        with pytest.raises(RuntimeError):
            async with Reader(f1, 4, 12) as f2:
                pass
    async with Reader(Reader("tests/data/example.text"), 4, 12) as f:
        assert (await f.read()) == b"12345678"


def test_reader():
    asyncio.get_event_loop().run_until_complete(atest_reader())
