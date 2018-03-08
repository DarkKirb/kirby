import sys
import yaml

def makeYAMLtype(f):
    v = int.from_bytes(f.read(4),'little')
    if v == 1:
        return YAMLInt(f)
    elif v == 2:
        return YAMLFloat(f)
    elif v == 3:
        return YAMLBool(f)
    elif v == 4:
        return YAMLString(f)
    elif v == 5:
        return YAMLDict(f)
    elif v == 6:
        return YAMLList(f)
    else:
        print(f.tell())
        print(v)
        return None
def readYAMLstring(f):
    length = int.from_bytes(f.read(4), 'little')
    return f.read(length).decode("UTF-8")
class YAML:
    def __init__(self, f):
        assert f.read(4) == b"XBIN"
        f.read(2)
        if f.read(1) == b'\x02':
            f.seek(0x10)
        else:
            f.seek(0x14)
        assert f.read(4) == b"YAML"
        self.version = int.from_bytes(f.read(4), 'little')
        self.content = makeYAMLtype(f)


class YAMLDict():
    def __new__(cls, f):
        count = int.from_bytes(f.read(4), 'little')
        keys=[]
        values=[]
        for i in range(count):
            keys.append(int.from_bytes(f.read(4), 'little'))
            values.append(int.from_bytes(f.read(4), 'little'))
        content = {}
        off=f.tell()
        for i in range(count):
            f.seek(keys[i])
            key = readYAMLstring(f)
            f.seek(values[i])
            val = makeYAMLtype(f)
            content[key] = val
        f.seek(off)
        return content

class YAMLList():
    def __new__(cls, f):
        count = int.from_bytes(f.read(4), 'little')
        values=[]
        for i in range(count):
            values.append(int.from_bytes(f.read(4), 'little'))
        content = []
        off=f.tell()
        for i in range(count):
            f.seek(values[i])
            content.append(makeYAMLtype(f))
        f.seek(off)
        return content

class YAMLString():
    def __new__(cls, f):
        f.seek(int.from_bytes(f.read(4), 'little'))
        return readYAMLstring(f)

class YAMLInt():
    def __new__(cls, f):
        return int.from_bytes(f.read(4), 'little')
import struct
class YAMLFloat():
    def __new__(cls, f):
        return struct.unpack("<f",f.read(4))[0]

class YAMLBool():
    def __new__(cls, f):
        return bool(int.from_bytes(f.read(4), 'little'))

if __name__ == "__main__":
    with open(sys.argv[1],"rb") as f:
        y=YAML(f)
        print(yaml.dump(y.content, default_flow_style=False, allow_unicode=True))
