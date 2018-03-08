import sys
import yaml
import io
import os
from yaml_to_xbin import create_xbin
string_relocs=[]

repoint=[]
def add_reloc(data, pos, rv, relative=False, offset=0):
    p = pos
    if relative:
        p = int.from_bytes(data[p:p+4], 'little') + offset*4
    x = int.from_bytes(data[p:p+4], 'little')
    x -= rv
    data[p:p+4] = x.to_bytes(4, 'little')
    repoint.append((pos, relative, offset))
def do_reloc(data, pos, off, relative, offset):
    p = pos
    if relative:
        p = int.from_bytes(data[p:p+4], 'little') + offset*4
    x = int.from_bytes(data[p:p+4], 'little')
    x += off
    data[p:p+4] = x.to_bytes(4, 'little')
def begin_relocs(orig):
    global repoint
    relocval = int.from_bytes(orig[0x1C:0x20], 'little')
    add_reloc(orig, 0x1C, relocval, True)
    add_reloc(orig, 0x1C, relocval)
    add_reloc(orig, 0x20, relocval, True, 0)
    add_reloc(orig, 0x20, relocval, True, 1)
    add_reloc(orig, 0x20, relocval, True, 2)
    add_reloc(orig, 0x20, relocval, True, 3)
    add_reloc(orig, 0x20, relocval, True, 4)
    add_reloc(orig, 0x20, relocval)
    add_reloc(orig, 0x24, relocval)
    repoint=repoint[::-1]


def end_relocs(orig, o):
    for pos, relative, offset in repoint:
        do_reloc(orig, pos, o, relative, offset)
    repoint.clear()


def relocate_section(data, off):
    length = int.from_bytes(data[:4], 'little')
    for i in range(length):
        offset = int.from_bytes(data[(i+1)*4:(i+2)*4], 'little')
        offset += off
        data = data[:(i+1)*4] + offset.to_bytes(4, 'little') + data[(i+2)*4:]
    return data

def pad(data, byte):
    d = data + bytes(byte - len(data) % byte)
    return d

def pack_xbins(yamllist):
    data = len(yamllist).to_bytes(4, 'little')
    ydata = b''
    off = len(yamllist)*4+4
    for p in yamllist:
        data += (off + len(ydata)).to_bytes(4, 'little')
        t = bytearray(create_xbin(p))
        t[0xC:0x10] = b'\x9f\x4e\0\0'
        ydata += t
    return pad(data + ydata, 64)

def pack_metadata(songname, lightingname, metadata, pos):
    print(hex(pos))
    songname = songname.encode("UTF-8")
    lightingname = lightingname.encode("UTF-8")
    string_relocs.append((pos, songname))
    string_relocs.append((pos+4, lightingname))
    data = bytes(8)
    for x in metadata:
        data += x.to_bytes(4, 'little')
    return data

def set_data(orig, data):
    orig = bytearray(orig)
    o = int.from_bytes(orig[0x1c:0x20], 'little')
    loc = int.from_bytes(orig[0x18:0x1C], 'little')
    begin_relocs(orig)
    t = orig[:loc] + relocate_section(pack_xbins(data["carryable items"]), loc)
    newoff = len(t)
    orig = bytearray(t + orig[o:])
    end_relocs(orig, newoff)
    orig = orig[:int.from_bytes(orig[0x24:0x28], 'little')]
    orig[0x24:0x28] = len(orig).to_bytes(4, 'little')
    orig += pack_metadata(data["musicname"], data["lightingname"], data["metadata"], len(orig))
    objects = pack_xbins(data["objects"])
    orig[0x28:0x2C] = len(orig).to_bytes(4, 'little')
    orig += relocate_section(objects, len(orig))
    items = pack_xbins(data["items"])
    orig[0x2C:0x30] = len(orig).to_bytes(4, 'little')
    orig += relocate_section(items, len(orig))
    unknown1 = pack_xbins(data["bosses"])
    orig[0x30:0x34] = len(orig).to_bytes(4, 'little')
    orig += relocate_section(unknown1, len(orig))
    enemies = pack_xbins(data["enemies"])
    orig[0x34:0x38] = len(orig).to_bytes(4, 'little')
    orig += relocate_section(enemies, len(orig))
    orig[0x38:0x3C] = len(orig).to_bytes(4, 'little')
    orig += bytes(4)
    bgnameoff = int.from_bytes(orig[0x20:0x24], 'little')
    string_relocs.append((bgnameoff, data["background"].encode("UTF-8")))
    string_relocs.append((bgnameoff+4, data["tileset"].encode("UTF-8")))
    for pos, s in string_relocs:
        orig[pos:pos+4] = len(orig).to_bytes(4, 'little')
        orig += len(s).to_bytes(4, 'little')
        orig += s
        orig += bytes(4-len(orig)%4)
    x = b'XBIN\x34\x12\x02\0' + len(orig).to_bytes(4, 'little') + b'\xe9\xfd\0\0'
    return x+orig[16:]

if __name__ == "__main__":
    with open(sys.argv[1], "r") as f:
        data = yaml.load(f.read())
    with open(os.path.splitext(sys.argv[1])[0] + ".dat", "rb") as f:
        leveldata = f.read()
    leveldata = set_data(leveldata, data)
    with open(os.path.splitext(sys.argv[1])[0] + ".dat", "wb") as f:
        f.write(leveldata)
