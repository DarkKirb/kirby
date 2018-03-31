from kirby.utils.reader import Reader, ABytesIO, FileExtensionError
from kirby.rom.rom import ROM, GBROM
import asyncio
import pytest


def async_test(f):
    def wrapper(*args, **kwargs):
        return asyncio.get_event_loop().run_until_complete(f(*args, **kwargs))
    return wrapper


@async_test
async def test_reader():
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
            await f2.seek(0)
            assert await f2.write(b"1") == 1
        assert (await f1.seek(1, 2)) == 16
        assert (await f1.seek(-4, 1)) == 12
        assert (await f1.read()) == b"1234\n"
        with pytest.raises(RuntimeError):
            async with Reader(f1, 4, 12) as f2:
                pass
    async with Reader(Reader("tests/data/example.text"), 4, 12) as f:
        assert (await f.read()) == b"12345678"


@async_test
async def test_rom():
    async with ROM(ABytesIO()) as f:
        example_text = """This is an example text that contains unicode
        characters, and linebreaks, for example these: äöüßÄÖÜẞſテキスト
        uiae nrtd"""
        await f.write(0, example_text)
        new_text = await f.read(0, "s")
        assert example_text == new_text
    async with ROM(ABytesIO()) as f:
        await f.write(0, 0, "b")
        await f.write(1, 1, "h")
        await f.write(3, 3, "a")
        await f.write(6, 6, "i")
        with pytest.raises(RuntimeError):
            await f.write(10, 2**32)
        assert await f.read(0, "b") == 0
        assert await f.read(1, "h") == 1
        assert await f.read(3, "a") == 3
        assert await f.read(6, "i") == 6
        with pytest.raises(RuntimeError):
            await f.read(10, "j")
        await f.memset(0, 10, b"\0")
        assert await f.read(0, 10) == bytes(10)

    async with ROM(ABytesIO(bytes(50))) as f:
        assert await f.find_new_loc(10) == 0
        assert await f.find_new_loc(10, 5) == 5
        with pytest.raises(ValueError):
            await f.find_new_loc(10, end=5)
        with pytest.raises(ValueError):
            await f.find_new_loc(51)

    async with ROM(ABytesIO(b"\xAF\0\0\xFE\0\xFE\0\0\0")) as f:
        assert await f.find_new_loc(3) == 6
        addr = await f.relocate(b"ape")
        assert addr == 6
        assert await f.read(addr, 3) == b"ape"


@async_test
async def test_gbrom():
    async with GBROM(ABytesIO()) as f:
        assert f.bank == 1
        await f.bankswitch(100)
        assert f.bank == 100
        assert f.resolve(0) == 0
        await f.bankswitch(1)
        assert f.resolve(0x2000) == 0x2000
        await f.bankswitch(2)
        assert f.resolve(0x2000) == 0x4000
        with pytest.raises(ValueError):
            f.resolve(0x4000)

        assert f.resolve(0x32000) == 0x6000


if __name__ == "__main__":
    test_rom()
