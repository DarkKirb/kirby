#!/usr/bin/env python3

patches={}
print("Reading patch")
with open("patch.ini") as f:
    for l in f.readlines():
        if l == "[OnFrame]\n":
            continue
        if l[0] == "$":
            continue
        l=l[:-1]
        addr, t, data = l.split(":")
        addr = int(addr, 16)
        data = int(data, 16)
        if addr < 0x800041C0:
            continue
        addr -= 0x800041C0
        if t == "byte":
            patches[addr] = data
        elif t == "word":
            patches[addr] = data >> 8
            patches[addr+1] = data & 255
        elif t == "dword":
            patches[addr] = data >> 24
            patches[addr+1] = (data >> 16) & 255
            patches[addr+2] = (data >> 8) & 255
            patches[addr+3] = data & 255

print("Patching {} bytes".format(len(patches.keys())))

with open("in.dol","rb") as f1:
    with open("out.dol", "wb") as f2:
        for a, b in patches.items():
            if f1.tell() < a:
                f2.write(f1.read(a-f1.tell()))
            f2.write(bytes([b]))
            f1.read(1)
        f2.write(f1.read())


