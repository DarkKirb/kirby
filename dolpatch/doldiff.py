
print("[OnFrame]")
with open("in.dol", "rb") as f1:
    f1.seek(0, 2)
    l = f1.tell()
    f1.seek(0)
    with open("out.dol", "rb") as f2:
        for i in range(0,l,4):
            a = f1.read(4)
            b = f2.read(4)
            if a != b:
                print("0x{:X}:dword:0x{:X}".format(i+0x800041C0, int.from_bytes(b, 'big')))

