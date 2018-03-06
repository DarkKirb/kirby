import enums
import struct
class Linker:
    def __init__(self, off, endian):
        self.objects = []
        self.off = off
        self.endian = endian

    def link(self, offset, data):
        for obj in self.objects:
            obj.link(self.off + offset)

    def __iadd__(self, obj):
        if not isinstance(obj, Linker):
            return NotImplemented
        self.objects.append(obj)

class LinkableObject(Linker):
    def __init__(self, off, endian):
        super().__init__(off, endian)

    def link(self, offset, data):
        ps = ">I" if self.endian == enums.Endian.BIG else "<I"
        self.data[self.off + offset:self.off + offset + 4] = struct.pack(ps, struct.unpack(ps)[0]+offset)
