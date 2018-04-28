"""
This module contains a class used for reading and writing parts of files asynchronously, as if they were files.
"""

import aiofiles
import io


class Reader:
    """Reader class. Can also write data. All methods are asynchronous"""

    def __init__(self, fname, start=None, end=None, opened=False):
        """Initialized the reader

        Args:
        =========
        fname: str, Reader or any other object that has compatible API to Reader
        start: int, optional. If start is None, the start will be the current position of the file handle when entering
        end: int, optional. If end is None, the end will be the end of file. If it is, length extension will be possible
        opened: bool, optional. If opened equals True, the file handle won't be opened or closed when entering or exiting
        """
        self.fname = fname
        if isinstance(fname, str):
            self.fh = aiofiles.open(fname, mode="r+b")
        else:
            self.fh = fname

        if opened:
            self.f = fname
        else:
            self.f = None

        self.opened = opened

        self.start = start
        self.end = end
        self.entered = False
        self.off = 0

    async def __aenter__(self):
        """Initializes internals. This will set self.f if self.opened equals to False, self.start and self.end if they are none"""
        if self.entered:
            raise RuntimeError(
                "You need to pass opened=True if you want to chain an already active Reader in a Reader!")

        if self.f is None:
            self.f = await self.fh.__aenter__()

        if self.start is None:
            self.start = await self.f.tell()

        if self.end is None:
            x = await self.f.tell()
            await self.f.seek(0, 2)
            self.end = await self.f.tell()
            await self.f.seek(x)

        self.entered = True
        return self

    async def __aexit__(self, *e):
        """Closes the file handle if self.opened equals to True"""
        if not self.opened:
            await self.fh.__aexit__(*e)

    def size(self):
        """Returns the size of the file"""
        return self.end - self.start

    async def flush(self):
        """Flushes the file to disk"""
        await self.f.flush()

    async def read(self, size=None):
        """Read data. The argument size behaves exactly like on file objects"""
        start = await self.tell()

        if size is None:
            end = self.size()
        else:
            end = start + size
            if end >= self.size():
                end = self.size()

        x = await self.f.tell()
        await self.f.seek(self.start + start)
        data = await self.f.read(end - start)
        self.off += end - start
        await self.f.seek(x)
        return data

    async def write(self, data):
        """Write data. The argument data behaves exactly like on file objects, with the only difference that length extension is not always possible"""
        start = await self.tell()
        end = start + len(data)

        if self.opened:
            # it's unsafe to extend the file, so check for that
            if end >= self.size():
                raise FileExtensionError(
                    "It's unsafe to write past the end of the file!")
        else:
            self.end = max(self.end, end)

        x = await self.f.tell()
        await self.f.seek(self.start + start)
        t = await self.f.write(data)
        self.off += end - start
        await self.f.seek(x)
        return t

    async def seek(self, i, off=0):
        """Seeks through the file. Arguments behave exactly like on file objects"""
        if off == 0:
            self.off = i
        if off == 1:
            self.off += i
        if off == 2:
            self.off = self.size() + i

        return self.off

    async def tell(self):
        """Gets the current position in file"""
        return self.off


class FileExtensionError(IOError):
    pass


class ABytesIO(io.BytesIO):
    async def __aenter__(self):
        return super().__enter__()

    async def __aexit__(self, *e):
        super().__exit__(*e)

    async def seek(self, i, pos=0):
        return super().seek(i, pos)

    async def tell(self):
        return super().tell()

    async def read(self, length=None):
        return super().read(length)

    async def write(self, data):
        return super().write(data)

    async def flush(self):
        return super().flush()
