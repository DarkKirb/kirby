from . import enums
import struct
class Linker:
    def __init__(self, off, endian):
        self.objects = []
        self.off = off
        self.endian = endian

    def link(self, offset, data):
        for obj in self.objects:
            obj.link(self.off + offset, data)

    def __iadd__(self, obj):
        if not isinstance(obj, Linker):
            return NotImplemented
        self.objects.append(obj)
        return self

class LinkableObject(Linker):
    def __init__(self, off, endian):
        super().__init__(off, endian)

    def link(self, offset, data):
        ps = ">I" if self.endian == enums.Endian.BIG else "<I"
        data[self.off:self.off + 4] = struct.pack(ps, struct.unpack(ps,data[self.off:self.off + 4])[0]+offset)
