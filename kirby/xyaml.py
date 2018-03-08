from . import xbin
import struct
from . import linker
import io
from . import enums
def read_yaml(fd):
    if not isinstance(fd, str):
        fd.seek(0)
    out_data={}
    with xbin.XBIN(fd) as f:
        out_data["xbinver"] = f.version
        out_data["endian"] = f.endian
        out_data["uid"] = f.uid
        out_data["type"] = f.type
        objects = {}
        assert f.read(4) == b"YAML"
        out_data["yamlver"] = int.from_bytes(f.read(4), str(f.endian))

        def make_type(off):
            if off in objects.keys():
                return objects[off]
            f.seek(off)
            i = int.from_bytes(f.read(4), str(f.endian))
            obj = None
            if i == 1:
                obj = int.from_bytes(f.read(4), str(f.endian))
            elif i == 2:
                obj, = struct.unpack("<f", f.read(4))
            elif i == 3:
                obj = int.from_bytes(f.read(4), str(f.endian)) != 0
            elif i == 4:
                o = int.from_bytes(f.read(4), str(f.endian))
                if o in objects.keys():
                    obj = objects[o]
                else:
                    f.seek(o)
                    l = int.from_bytes(f.read(4), str(f.endian))
                    objects[o] = f.read(l).decode()
                    obj = objects[o]
            elif i == 5:
                obj={}
                objects[off] = obj
                l = int.from_bytes(f.read(4), str(f.endian))
                keys = []
                vals = []
                for i in range(l):
                    keys.append(int.from_bytes(f.read(4), str(f.endian)))
                    vals.append(int.from_bytes(f.read(4), str(f.endian)))

                for ko,vo in zip(keys, vals):
                    if ko not in objects.keys():
                        f.seek(ko)
                        l = int.from_bytes(f.read(4), str(f.endian))
                        objects[ko] = f.read(l).decode()

                    k = objects[ko]
                    v = make_type(vo)
                    obj[k]=v
            elif i == 6:
                obj=[]
                objects[off] = obj
                l = int.from_bytes(f.read(4), str(f.endian))
                objs=[]
                for i in range(l):
                    objs.append(int.from_bytes(f.read(4), str(f.endian)))
                for o in objs:
                    obj.append(make_type(o))
            else:
                print(f"Unknown yaml tag at {f.tell()}")

            objects[off] = obj
            return obj

        out_data["data"] = make_type(f.tell())
        return out_data

def save_yaml(in_data, fast=False):
    """fast means that only objects that are literally the same will be deduplicated"""
    data=in_data["data"]
    objects=[]
    known_ids={}
    # Step 1: loading the data structure into objects
    def find_duplicate(o):
        for x in objects:
            if x != o:
                continue
            if type(x) is type(o):
                 return x
        return o
    def is_in(o):
        for x in objects:
            if x is o:
                return True
        return False

    def traverse(o):
        if not fast:
            o = find_duplicate(o)
        if id(o) in known_ids.keys():
            return known_ids[id(o)]
        if isinstance(o, (int, float, bool)):
            known_ids[id(o)] = o
            #leaf node
            if not is_in(o):
                objects.append(o)
            return o
        elif isinstance(o, dict):
            ndict = {}
            known_ids[id(o)] = ndict
            for k, v in o.items():
                ndict[traverse((k,None))] = traverse(v)
            if not fast:
                ndict = find_duplicate(ndict)
            if not is_in(ndict):
                objects.append(ndict)
            return ndict
        elif isinstance(o, str):
            known_ids[id(o)] = o
            if not is_in(o):
                objects.append(o)
                traverse((o,None))
            return o
        elif isinstance(o, tuple):
            known_ids[id(o)] = o
            if not is_in(o):
                objects.append(o)
            return o
        elif isinstance(o, list):
            nlist=[]
            known_ids[id(o)]=nlist
            for i in o:
                nlist.append(traverse(i))

            if not fast:
                nlist = find_duplicate(nlist)
            if not is_in(nlist):
                objects.append(nlist)
            return nlist
        print(type(o))
        return o

    t=traverse(data)

    #step 2: place t in front of the list
    index = objects.index(t)
    objects = [t] + objects[0:index] + objects[index+1:]

    #step 3: binarifying
    buf = bytearray()
    link = linker.Linker(0, "little")
    addrs = {}
    linkable = {}

    for obj in objects:
        addrs[id(obj)] = len(buf)
        if isinstance(obj, bool):
            buf += (3).to_bytes(4, "little")
            buf += obj.to_bytes(4, "little")
        elif isinstance(obj, int):
            buf += (1).to_bytes(4, "little")
            buf += obj.to_bytes(4, "little")
        elif isinstance(obj, float):
            buf += (2).to_bytes(4, "little")
            buf += struct.pack("<f", obj)
        elif isinstance(obj, str):
            buf += (4).to_bytes(4, "little")
            l = linker.LinkableObject(len(buf), "little")
            x = find_duplicate((obj, None))
            if id(x) not in linkable.keys():
                linkable[id(x)] = [l]
            else:
                linkable[id(x)].append(l)
            link += l
            buf += bytes(4)
        elif isinstance(obj, tuple):
            buf += len(obj[0]).to_bytes(4, "little")
            buf += obj[0].encode()
        elif isinstance(obj, dict):
            buf += (5).to_bytes(4, "little")
            buf += len(obj.keys()).to_bytes(4, "little")
            for k,v in obj.items():
                l = linker.LinkableObject(len(buf), "little")
                if id(k) not in linkable.keys():
                    linkable[id(k)] = [l]
                else:
                    linkable[id(k)].append(l)
                link += l
                buf += bytes(4)
                l = linker.LinkableObject(len(buf), "little")
                if id(v) not in linkable.keys():
                    linkable[id(v)] = [l]
                else:
                    linkable[id(v)].append(l)
                link += l
                buf += bytes(4)
        elif isinstance(obj, list):
            buf += (6).to_bytes(4, "little")
            buf += len(obj).to_bytes(4, "little")
            for i in obj:
                l = linker.LinkableObject(len(buf), "little")
                if id(i) not in linkable.keys():
                    linkable[id(i)] = [l]
                else:
                    linkable[id(i)].append(l)
                link += l
                buf += bytes(4)

    #Step 4: link everything

    for obj,addr in addrs.items():
        if not obj in linkable.keys():
            continue
        for fixup in linkable[obj]:
            fixup.link(addr, buf)


    x = xbin.XBIN(io.BytesIO())
    x.version = in_data["xbinver"]
    x.endian = in_data["endian"]
    x.uid = in_data["uid"]
    x.type = in_data["type"]
    x.init()

    x.write(b"YAML")
    x.write(in_data["yamlver"].to_bytes(4, str(in_data["endian"])))
    link.link(x.tell(), buf)
    x.write(buf)
    x.flush()
    x.seek(0)
    return x.read()

import argparse
import yaml
import random

def c_read_yaml():
    parser = argparse.ArgumentParser(description="Convert XBIN yaml files to yaml")
    parser.add_argument("file", metavar="file", type=str, help="File to convert")
    parser.add_argument("--output", "-o", dest="outfile", metavar="file", type=str, help="File to save to (default: stdout)", nargs="?")
    parser.add_argument("--no-metadata", dest="metadata", action="store_const", default=True, const=False, help="Disable metadata output")
    args=parser.parse_args()
    t = read_yaml(args.file)
    if not args.metadata:
        t = t["data"]
    s = yaml.dump(t, default_flow_style=False, allow_unicode=True)
    if args.outfile is None:
        print(s)
    else:
        with open(parser.outfile,"w") as f:
            f.write(s)

def c_write_yaml():
    parser = argparse.ArgumentParser(description="Convert yaml files to XBIN yaml")
    parser.add_argument("file", metavar="file", type=str, help="File to convert")
    parser.add_argument("--output", "-o", dest="outfile", metavar="file", type=str, help="File to save to", required=True)
    parser.add_argument("--new", dest="new", action="store_const", default=enums.XBINversion(2), const=enums.XBINversion(4), help="Use a version 4 xbin container (Default: guess/version 2)")
    parser.add_argument("--fast", dest="fast", action="store_const", default=False, const=True, help="Skip deduplication for faster conversion (larger file size, sometimes upwards of 10x as big when compressed. NOTE: the original assets are not deduplicated")
    parser.add_argument("--uid", dest="uid", metavar="uid", help="UID for v4 XBIN (default: guess/random)")
    args=parser.parse_args()
    with open(args.file) as f:
        data = yaml.load(f.read())

    can_guess = True
    if not isinstance(data, dict):
        can_guess = False
    elif ("xbinver" not in data) or ("endian" not in data) or ("uid" not in data) or ("yamlver" not in data) or ("data" not in data) or ("type" not in data):
        can_guess = False

    if can_guess:
        bindata = save_yaml(data, args.fast)
    else:
        indata = {}
        indata["xbinver"] = args.new
        indata["endian"] = enums.Endian.LITTLE
        indata["type"] = enums.XBINtype.MAIN
        indata["yamlver"] = 2
        indata["uid"] = args.uid if args.uid is not None else random.getrandbits(32)
        indata["data"] = data
        bindata = save_yaml(data, args.fast)

    with open(args.outfile, "wb") as f:
        f.write(bindata)

