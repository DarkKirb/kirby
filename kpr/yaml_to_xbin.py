import sys
import yaml
import os
import struct

objects=[]
relink=[]
def add_reloc(pos, obj):
    if not isinstance(obj, LinkableObject):
        print(obj)
        raise ValueError("Has to be a linkable object!")
    relink.append((pos, obj))

class LinkableObject(object):
    def __new__(cls, value):
        o = super().__new__(cls)
        o.__init__(value)
        if o in objects:
            return objects[objects.index(o)]
        o.id = len(objects)
        objects.append(o)
        return o

    def __init__(self, value):
        self.value = value
    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.value == other.value



class Integer(LinkableObject):
    def __init__(self, value):
        super().__init__(value)

    def compile(self, pos):
        data = b'\x01\0\0\0'
        return data + self.value.to_bytes(4, 'little')

class Float(LinkableObject):
    def __init__(self, value):
        super().__init__(value)
    def compile(self, pos):
        data = b'\x02\0\0\0'
        return data + struct.pack("<f", self.value)

class Boolean(LinkableObject):
    def __init__(self, value):
        super().__init__(value)
    def compile(self, pos):
        data = b'\x03\0\0\0'
        data += b'\x01\0\0\0' if self.value else bytes(4)
        return data

class String(LinkableObject):
    def __init__(self, value):
        super().__init__(value)
    def compile(self, pos):
        v = self.value.encode("UTF-8")
        data = len(v).to_bytes(4, 'little')
        data += v
        l = len(v)
        data += bytes(4 - (l % 4)) #Align to next 32-bit boundary
        return data
    def __hash__(self):
        return hash(self.value)

class StringRef(LinkableObject):
    def __new__(cls, value):
        x = super().__new__(cls, (str, value))
        x.string = String(value)
        return x
    def __init__(self, value):
        super().__init__(value)
    def compile(self, pos):
        data = b'\x04\0\0\0'
        data += bytes(4)
        add_reloc(pos+4, self.string)
        return data

class Dict(LinkableObject):
    def __new__(cls, value):
        contents={}
        for k,v in value.items():
            k_s = String(k)
            v_s = create_type(v)
            contents[k_s] = v_s

        x=super().__new__(cls, contents)
        x.v=contents
        return x
    def __init__(self, value):
        super().__init__(value)
    def compile(self, pos):
        data = b'\x05\0\0\0'
        data += len(self.v.keys()).to_bytes(4, 'little')
        for k, v in self.v.items():
            add_reloc(pos+len(data), k)
            data+=bytes(4)
            add_reloc(pos+len(data), v)
            data+=bytes(4)
        return data

class List(LinkableObject):
    def __new__(cls, value):
        contents=[]
        for v in value:
            contents.append(create_type(v))

        x=super().__new__(cls, contents)
        x.v=contents
        return x
    def __init__(self, value):
        super().__init__(value)
    def compile(self, pos):
        data = b'\x06\0\0\0'
        data += len(self.value).to_bytes(4, 'little')
        for v in self.v:
            add_reloc(pos+len(data), v)
            data+=bytes(4)
        return data

def create_type(d):
    if d is None:
        print(d)
    if isinstance(d, bool):
        return Boolean(d)
    elif isinstance(d, int):
        return Integer(d)
    elif isinstance(d, float):
        return Float(d)
    elif isinstance(d, str):
        return StringRef(d)
    elif isinstance(d, dict):
        return Dict(d)
    elif isinstance(d, list) or isinstance(d, tuple):
        return List(d)
    raise ValueError(repr(d))

def deduplicate(data):
    global objects
    print("Deduplicating the data")
    d=create_type(data)
    index = objects.index(d)
    begin = objects[:index]
    end = objects[index+1:]
    objects = [d] + begin + end

def compile():
    print("Compiling {} objects".format(len(objects)))
    data = b'YAML\x02\0\0\0'
    for o in objects:
        o.off=len(data)+16
        data+=o.compile(o.off)
    return data

def link(data):
    data=b'XBIN\x34\x12\02\0' + (len(data)+16).to_bytes(4, 'little') + b'\xe9\xfd\0\0' + data
    print("Doing {} relocations".format(len(relink)))
    for offset, obj in relink:
        begin = data[:offset]
        end = data[offset+4:]
        data = begin + obj.off.to_bytes(4, 'little') + end
    return data

def create_xbin(data):
    global objects
    global relink
    deduplicate(data)
    data = link(compile())
    objects=[]
    relink=[]
    return data

if __name__ == "__main__":
    with open(sys.argv[1], "r") as f:
        data = yaml.load(f.read())
    bindata = create_xbin(data)
    with open(os.path.splitext(sys.argv[1])[0]+".bin", "wb") as f:
        f.write(bindata)
