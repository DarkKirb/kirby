from kirby.utils.reader import Reader, ABytesIO, FileExtensionError
from kirby.rom.rom import ROM
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


async def atest_rom():
    async with ROM(ABytesIO()) as f:
        example_text = """This is an example text that contains unicode
        characters, and linebreaks, for example these: äöüßÄÖÜẞſテキスト
        uiae nrtd"""
        await f.write(0, example_text)
        new_text = await f.read(0, "s")
        print(new_text)
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


def test_reader():
    asyncio.get_event_loop().run_until_complete(atest_reader())


def test_rom():
    asyncio.get_event_loop().run_until_complete(atest_rom())


if __name__ == "__main__":
    test_rom()
