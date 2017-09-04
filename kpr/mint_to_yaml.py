import struct
import yaml
import io
import sys
def deref(f):
    off=int.from_bytes(f.read(4), 'little')
    o=f.tell()
    f.seek(off)
    x=int.from_bytes(f.read(4), 'little')
    f.seek(o)
    return off, x

def get_function_section(f,off):
    o=f.tell()
    f.seek(off)
    count = int.from_bytes(f.read(4), 'little')
    function_offsets = []
    functions = []
    for i in range(count):
        function_offsets.append(int.from_bytes(f.read(4), 'little'))
    for fun in function_offsets:
        f.seek(fun)
        fnameoff, uid = struct.unpack("<II", f.read(8))
        f.seek(fnameoff)
        fnamelen = int.from_bytes(f.read(4), 'little')
        functions.append({"name":f.read(fnamelen).decode("UTF-8"), "uid":uid})
    f.seek(o)
    return functions

def get_enum_section(f, off):
    o=f.tell()
    f.seek(off)
    count = int.from_bytes(f.read(4), 'little')
    enum_offsets = []
    enums = {}
    for i in range(count):
        enum_offsets.append(int.from_bytes(f.read(4), 'little'))
    for en in enum_offsets:
        f.seek(en)
        valoff, val = struct.unpack("<II", f.read(8))
        f.seek(valoff)
        vallen = int.from_bytes(f.read(4), 'little')
        enums[f.read(vallen).decode("UTF-8")] = val
    f.seek(o)
    return enums

def get_object_section(f, off):
    o=f.tell()
    f.seek(off)
    count = int.from_bytes(f.read(4), 'little')
    object_offset = []
    object_contents = []
    for i in range(count):
        object_offset.append(int.from_bytes(f.read(4), 'little'))
    for obj in object_offset:
        f.seek(obj)
        var_off, uid, type_off, default = struct.unpack("<IIII", f.read(16))
        f.seek(var_off)
        var_len = int.from_bytes(f.read(4), 'little')
        var_name = f.read(var_len).decode("UTF-8")
        f.seek(type_off)
        type_len = int.from_bytes(f.read(4), 'little')
        type_name = f.read(type_len).decode("UTF-8")
        object_contents.append({"name":var_name,"type":type_name,"uid":uid,"default":default})
    f.seek(o)
    return object_contents



def get_bytecode_yaml(bc):
    f=io.BytesIO(bc)
    assert b"XBIN\x34\x12\x02\0" == f.read(8)
    f.read(8)
    f.seek(int.from_bytes(f.read(4), 'little'))
    l = int.from_bytes(f.read(4), 'little')
    name = f.read(l).decode("UTF-8")

    f.seek(0x14)

    sections = struct.unpack("<III", f.read(12))
    sections_list=[]
    for no,s in enumerate(sections):
        if no == 0:
            l = int.from_bytes(f.read(4), 'little')
            f.read(4)
            sections_list.append({"bytecode": f.read(l)})
            continue
        if no == 1:
            l = int.from_bytes(f.read(4), 'little')
            sections_list.append({"bytecode": f.read(l*4)})
            continue
        stuff=[]
        f.seek(s)
        c = int.from_bytes(f.read(4), 'little')
        for i in range(c):
            stuffoff = int.from_bytes(f.read(4), 'little')
            o=f.tell()
            f.seek(stuffoff)
            nameoff = int.from_bytes(f.read(4), 'little')
            uid = int.from_bytes(f.read(4), 'little')
            code_s=[
                    dict(zip(("offset","length"), deref(f))),
                    dict(zip(("offset","length"), deref(f))),
                    dict(zip(("offset","length"), deref(f))),
                    dict(zip(("offset","length"), deref(f)))
                    ]
            code_s[0] = get_object_section(f, code_s[0]["offset"])
            code_s[1] = get_function_section(f, code_s[1]["offset"])
            code_s[2] = get_enum_section(f, code_s[2]["offset"])
            f.seek(nameoff)
            nl = int.from_bytes(f.read(4), 'little')
            x=f.read(nl)
            stuff.append({"name":x.decode("UTF-8"), "uid":uid, "sections":code_s})
            f.seek(o)
        sections_list.append(stuff)

    return {"name":name, "sections":sections_list}


def get_mint_file(f):
    assert b"XBIN\x34\x12\x02\0" == f.read(8)
    f.read(8)
    assert b"\01\x01\x03\0" == f.read(4)
    f.read(8)
    count, off=struct.unpack("<II", f.read(8))
    f.seek(off)
    xbins = {}
    for i in range(count):
        name, o = struct.unpack("<II", f.read(8))
        x=f.tell()
        f.seek(name)
        l=struct.unpack("<I", f.read(4))[0]
        n = f.read(l)
        f.seek(o+8)
        objlen = struct.unpack("<I", f.read(4))[0]
        f.seek(o)
        obj = f.read(objlen)
        xbins[n.decode("UTF-8")]=get_bytecode_yaml(obj)
        f.seek(x)
    return xbins

if __name__ == "__main__":
    with open(sys.argv[1], "rb") as f:
        print(yaml.dump(get_mint_file(f), default_flow_style=False))
