from .. import xbin, enums
from . import rtdl

class MintFile(xbin.XBIN):
    def __enter__(self):
        super().__enter__()
        if str(self.endian) == "big":
            assert self.read(4) == b'\0\x02\0\0'
        name_pos = int.from_bytes(self.read(4), str(self.endian))
        p = self.tell()
        self.seek(name_pos)
        name_size = int.from_bytes(self.read(4), str(self.endian))
        print(self.read(name_size).decode())
        self.seek(p)
        sec1_pos = int.from_bytes(self.read(4), str(self.endian))
        sec2_pos = int.from_bytes(self.read(4), str(self.endian))
        sec3_pos = int.from_bytes(self.read(4), str(self.endian))
        sec4_pos = int.from_bytes(self.read(4), str(self.endian))
        print(sec1_pos, sec2_pos, sec3_pos, sec4_pos)
        if sec1_pos:
            self.seek(sec1_pos)
            self.sdata = SDataSection(self)
        if sec2_pos:
            self.seek(sec2_pos)
            XREFSection(self)
        if sec3_pos:
            self.seek(sec3_pos)
            ClassSection(self)
        return self


class MintSection:
    def __init__(self, f):
        self.f=f
        self.off = f.tell()

class SDataSection(MintSection):
    def __init__(self, f):
        super().__init__(f)
        self.size = int.from_bytes(f.read(4), str(f.endian))

    def __get__(self, index):
        if index > self.size:
            raise ValueError("Out of bounds")
        self.f.seek(self.off + index*4 + 4)
        return self.f.read(4)
    def __len__(self):
        return self.size

class XREFSection(MintSection):
    def __init__(self, f):
        def read_string():
            pos = int.from_bytes(f.read(4), str(f.endian))
            x = f.tell()
            f.seek(pos)
            print(hex(pos))
            size = int.from_bytes(f.read(4), str(f.endian))
            s = f.read(size).decode()
            f.seek(x)
            return s
        super().__init__(f)
        self.size = int.from_bytes(f.read(4), str(f.endian))
        self.strings = [read_string() for x in range(self.size)]

    def __get__(self, index):
        return self.strings[index]

    def __len__(self):
        return self.size

class ClassSection(MintSection):
    def __init__(self, f):
        super().__init__(f)
        self.size = int.from_bytes(f.read(4), str(f.endian))
        print(self.size)
        self.classes = []
        for i in range(self.size):
            currpos = f.tell() + 4
            f.seek(int.from_bytes(f.read(4), str(f.endian)))
            self.classes.append(rtdl.Class(f))
            f.seek(currpos)
