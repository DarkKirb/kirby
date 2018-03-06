import xbin
import struct
def read_yaml(fd):
    if not isinstance(fd, str):
        fd.seek(0)
    out_data={}
    with xbin.XBIN(fd) as f:
        out_data["xbinver"] = f.version
        out_data["endian"] = f.endian
        out_data["uid"] = f.uid
        objects = {}
        print(f.tell())
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
        print(objects)
        return out_data


