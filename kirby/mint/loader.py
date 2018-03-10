from .. import xbin, enums
from . import rtdl
import io

class MintColl(xbin.XBIN):
    def __enter__(self):
        super().__enter__()
        filecount = int.from_bytes(self.read(4), str(self.endian))
        def read_filepos():
            self.read(4)
            return int.from_bytes(self.read(4), str(self.endian))
        filepos = [read_filepos() for f in range(filecount)]
        self.mints=[]
        for pos in filepos:
            self.seek(pos+8)
            l = int.from_bytes(self.read(4), str(self.endian))
            self.seek(pos)
            self.mints.append(MintFile(io.BytesIO(self.read(l))).__enter__())

        return self

    def strgen(self):
        for mint in self.mints:
            yield from mint.strgen()


class MintFile(xbin.XBIN):
    def __enter__(self):
        super().__enter__()
        if str(self.endian) == "big":
            assert self.read(4) == b'\0\x02\0\0'
        name_pos = int.from_bytes(self.read(4), str(self.endian))
        p = self.tell()
        self.seek(name_pos)
        name_size = int.from_bytes(self.read(4), str(self.endian))
        self.name=self.read(name_size).decode()
        self.seek(p)
        sec1_pos = int.from_bytes(self.read(4), str(self.endian))
        sec2_pos = int.from_bytes(self.read(4), str(self.endian))
        sec3_pos = int.from_bytes(self.read(4), str(self.endian))
        sec4_pos = int.from_bytes(self.read(4), str(self.endian))
        if sec1_pos:
            self.seek(sec1_pos)
            self.sdata = SDataSection(self)
        if sec2_pos:
            self.seek(sec2_pos)
            self.xrefs=XREFSection(self)
        if sec3_pos:
            self.seek(sec3_pos)
            self.classes=ClassSection(self)
        return self

    def strgen(self):
        yield f"//Begin of mint binary {self.name}"
        for cls in self.classes:
            yield from cls.strgen()

class MintSection:
    def __init__(self, f):
        self.f=f
        self.off = f.tell()

class SDataSection(MintSection):
    def __init__(self, f):
        super().__init__(f)
        self.size = int.from_bytes(f.read(4), str(f.endian))

    def __getitem__(self, index):
        if index > self.size:
            raise ValueError("Out of bounds")
        x=self.f.tell()
        self.f.seek(self.off + index + 4)
        val = self.f.read(4)
        self.f.seek(x)
        return val
    def __len__(self):
        return self.size

class XREFSection(MintSection):
    def __init__(self, f):
        def read_string():
            pos = int.from_bytes(f.read(4), str(f.endian))
            x = f.tell()
            f.seek(pos)
            size = int.from_bytes(f.read(4), str(f.endian))
            s = f.read(size).decode()
            f.seek(x)
            return s
        super().__init__(f)
        self.size = int.from_bytes(f.read(4), str(f.endian))
        self.strings = [read_string() for x in range(self.size)]

    def __getitem__(self, index):
        return self.strings[index]

    def __len__(self):
        return self.size

class ClassSection(MintSection):
    def __init__(self, f):
        super().__init__(f)
        self.size = int.from_bytes(f.read(4), str(f.endian))
        self.classes = []
        for i in range(self.size):
            currpos = f.tell() + 4
            f.seek(int.from_bytes(f.read(4), str(f.endian)))
            self.classes.append(rtdl.Class(f))
            f.seek(currpos)

    def __iter__(self):
        return (x for x in self.classes)
