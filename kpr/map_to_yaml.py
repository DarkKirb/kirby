import sys
import yaml
import io
from xbin_to_yaml import YAML
def get_xbin_len(f):
    assert f.read(4) == b"XBIN"
    f.read(4)
    return int.from_bytes(f.read(4), 'little')
def dump_xbins(f, p):
    f.seek(p)
    l = int.from_bytes(f.read(4), 'little')
    data = []
    for i in range(l):
        p = int.from_bytes(f.read(4), 'little')
        o = f.tell()
        f.seek(p)
        l = get_xbin_len(f)
        f.seek(p)
        data.append(f.read(l))
        f.seek(o)
    return (data)
def getStr(f):
    o=f.tell()
    f.seek(int.from_bytes(f.read(4), 'little'))
    s = f.read(int.from_bytes(f.read(4), 'little'))
    f.seek(o)
    return s.decode("UTF-8")
def read_room(f):
    assert f.read(4) == b"XBIN"
    f.seek(16)
    assert f.read(4) == b"\x0b\0\0\0"
    until = int.from_bytes(f.read(4), 'little')
    x=[]
    while f.tell() < until - 4:
        x.append(int.from_bytes(f.read(4), 'little'))
    f.seek(x[3])
    songname = getStr(f)
    f.read(4)
    lightingname = getStr(f)
    f.read(4)
    metadata = [ int.from_bytes(f.read(4), 'little') for i in range(14) ]
    f.seek(x[2])
    bgname = getStr(f)
    f.read(4)
    tilesetname = getStr(f)
    data = {
        "lightingname":lightingname,
        "musicname":songname,
        "metadata":metadata,
        "carryable items":[YAML(io.BytesIO(x)).content for x in dump_xbins(f, x[0])],
        "objects":[YAML(io.BytesIO(x)).content for x in dump_xbins(f, x[4])],
        "items":[YAML(io.BytesIO(x)).content for x in dump_xbins(f, x[5])],
        "bosses":[YAML(io.BytesIO(x)).content for x in dump_xbins(f, x[6])],
        "enemies":[YAML(io.BytesIO(x)).content for x in dump_xbins(f, x[7])],
        "background":bgname,
        "tileset":tilesetname
            }
    return data

if __name__ == "__main__":
    print(yaml.dump(read_room(open(sys.argv[1], "rb")), default_flow_style=False))
