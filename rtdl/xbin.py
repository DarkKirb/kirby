import enums
class XBIN(object):
    def __init__(self, fd):
        if isinstance(fd, str):
            fd = open(fd, "r+b")
        self.fd = fd

    def init(self):
        self.fd.seek(0)
        if self.version == enums.XBINversion(4):
            self.fd.write(bytes(20))
        else:
            self.fd.write(bytes(16))

    def __enter__(self):
        fd = self.fd
        assert fd.read(4) == b'XBIN'
        self.endian = enums.Endian.BIG if fd.read(2) == b'\x12\x34' else enums.Endian.LITTLE
        self.version = enums.XBINversion(int.from_bytes(fd.read(2), 'little'))
        self.length = int.from_bytes(fd.read(4), str(self.endian))
        self.type = int.from_bytes(fd.read(4), str(self.endian))
        self.uid = None if self.version == enums.XBINversion.ORIGINAL else int.from_bytes(fd.read(4), str(self.endian))
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        f=self.fd
        self.fd.seek(0,2)
        size = self.fd.tell()
        f.seek(0)
        f.write(b"XBIN" + (0x1234).to_bytes(2, str(self.endian)) + self.version.value.to_bytes(2, "little") + size.to_bytes(4, str(self.endian)))
        if self.version == enums.XBINversion.NEW:
            f.write(self.uid.to_bytes(4, str(self.endian)))

        f.flush()
        f.close()

    def tell(self):
        return self.fd.tell()

    def seek(self, pos, x=0):
        return self.fd.seek(pos, x)

    def read(self, *args, **kwargs):
        return self.fd.read(*args, **kwargs)

    def write(self, *args, **kwargs):
        return self.fd.write(*args, **kwargs)

    def truncate(self):
        return self.fd.truncate()


