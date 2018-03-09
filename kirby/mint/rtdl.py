#RTDL specifics

class Class:
    def __init__(self, f):
        self.f = f
        self.off = f.tell()
        name_ptr = int.from_bytes(f.read(4), str(f.endian))
        fields_ptr = int.from_bytes(f.read(4), str(f.endian))
        methods_ptr = int.from_bytes(f.read(4), str(f.endian))
        f.seek(name_ptr)
        name_len = int.from_bytes(f.read(4), str(f.endian))
        self.name = f.read(name_len).decode()
        print(self.name)

        f.seek(fields_ptr)
        fields_count = int.from_bytes(f.read(4), str(f.endian))
        fields_pos=[int.from_bytes(f.read(4), str(f.endian)) for x in range(fields_count)]

        f.seek(methods_ptr)
        methods_count = int.from_bytes(f.read(4), str(f.endian))
        methods_pos=[int.from_bytes(f.read(4), str(f.endian)) for x in range(methods_count)]

        def do_field(pos):
            f.seek(pos)
            return Field(f)
        self.fields = [do_field(pos) for pos in fields_pos]

        def please_never_do_meth(pos):
            f.seek(pos)
            return Method(f)
        self.fields = [please_never_do_meth(pos) for pos in methods_pos]

class Field:
    def __init__(self, f):
        self.f = f
        self.off = f.tell()

        name_ptr = int.from_bytes(f.read(4), str(f.endian))
        typename_ptr = int.from_bytes(f.read(4), str(f.endian))
        self.flags = int.from_bytes(f.read(4), str(f.endian))

        f.seek(name_ptr)
        name_size = int.from_bytes(f.read(4), str(f.endian))
        self.name = f.read(name_size).decode()

        f.seek(typename_ptr)
        typename_size = int.from_bytes(f.read(4), str(f.endian))
        self.typename = f.read(typename_size).decode()

        print(f"{self.name} is of type {self.typename} ({self.flags})")

class Method:
    def __init__(self, f):
        self.f = f
        self.off = f.tell()

        name_ptr = int.from_bytes(f.read(4), str(f.endian))
        self.code_ptr = int.from_bytes(f.read(4), str(f.endian))

        f.seek(name_ptr)
        name_size = int.from_bytes(f.read(4), str(f.endian))
        self.name = f.read(name_size).decode()

        print(f"Method {self.name} has code at {self.code_ptr}")
        f.seek(self.code_ptr)
        Code(f)

class InstructionDecoder:
    def __init__(self):
        self.insns={}
    def __iadd__(self, instruction):
        self.insns[instruction.no] = instruction
        return self
    def __call__(self, f):
        i = f.read(1)[0]
        if i in self.insns:
            return self.insns[i](f)
        return Ins(f, i)

class Ins:
    def __init__(self, f, no=None):
        self.n=no
        self.z = f.read(1)[0]
        self.x = f.read(1)[0]
        self.y = f.read(1)[0]
        self.v = self.x << 8 | self.y

    def __str__(self):
        return f"ins{hex(self.n)} r{self.z}, r{self.x}, r{self.y}, {hex(self.v)}"

class SetTrue(Ins):
    no = 0x01
    def __str__(self):
        return f"mov r{self.z}, true"

class SetFalse(Ins):
    no = 0x02
    def __str__(self):
        return f"mov r{self.z}, false"

class LoadSdataWord(Ins):
    no = 0x03
    def __str__(self):
        return f"ld r{self.z}, {hex(self.v)}"

class LoadSdataString(Ins):
    no = 0x04
    def __str__(self):
        return f"ld str r{self.z}, {hex(self.v)}"

class MovReg(Ins):
    no = 0x05
    def __str__(self):
        return f"mov r{self.z}, r{self.x}"

class MovRes(Ins):
    no = 0x06
    def __str__(self):
        return f"mov r{self.z}, res"

class SetArg(Ins):
    no = 0x07
    def __str__(self):
        return f"argset [{self.z}], r{self.x}"

class GetStatic(Ins):
    no = 0x09
    def __str__(self):
        return f"mov r{self.z}, [{hex(self.v)}]"

class DerefLoad(Ins):
    no = 0x0A
    def __str__(self):
        return f"mov r{self.z}, [r{self.x}]"

class Sizeof(Ins):
    no = 0x0B
    def __str__(self):
        return f"sizeof r{self.z}, class:{hex(self.v)}"

class DerefStore(Ins):
    no = 0x0C
    def __str__(self):
        return f"mov [r{self.z}], r{self.x}"

class StaticStore(Ins):
    no = 0x0D
    def __str__(self):
        return f"mov [{hex(self.v)}], r{self.z}"

class Addi(Ins):
    no = 0x0E
    def __str__(self):
        return f"addi r{self.z}, r{self.x}, r{self.y}"

class Subi(Ins):
    no = 0x0F
    def __str__(self):
        return f"subi r{self.z}, r{self.x}, r{self.y}"

class Muli(Ins):
    no = 0x10
    def __str__(self):
        return f"muli r{self.z}, r{self.x}, r{self.y}"

class Divi(Ins):
    no = 0x11
    def __str__(self):
        return f"divi r{self.z}, r{self.x}, r{self.y}"

class Modi(Ins):
    no = 0x12
    def __str__(self):
        return f"modi r{self.z}, r{self.x}, r{self.y}"

class Inci(Ins):
    no = 0x13
    def __str__(self):
        return f"inci r{self.z}, r{self.x}, r{self.y}"

class Negi(Ins):
    no = 0x14
    def __str__(self):
        return f"negi r{self.z}, r{self.x}, r{self.y}"

class Addf(Ins):
    no = 0x16
    def __str__(self):
        return f"addf r{self.z}, r{self.x}, r{self.y}"

class Subf(Ins):
    no = 0x17
    def __str__(self):
        return f"subf r{self.z}, r{self.x}, r{self.y}"

class Mulf(Ins):
    no = 0x18
    def __str__(self):
        return f"mulf r{self.z}, r{self.x}, r{self.y}"

class Divf(Ins):
    no = 0x19
    def __str__(self):
        return f"divf r{self.z}, r{self.x}, r{self.y}"

class Negf(Ins):
    no = 0x1c
    def __str__(self):
        return f"negf r{self.z}, r{self.x}, r{self.y}"

class Lti(Ins):
    no = 0x1d
    def __str__(self):
        return f"lti r{self.z}, r{self.x}, r{self.y}"

class Nei(Ins):
    no = 0x1e
    def __str__(self):
        return f"nei r{self.z}, r{self.x}, r{self.y}"

class Eqi(Ins):
    no = 0x1f
    def __str__(self):
        return f"eqi r{self.z}, r{self.x}, r{self.y}"

class Ltf(Ins):
    no = 0x21
    def __str__(self):
        return f"ltf r{self.z}, r{self.x}, r{self.y}"

class Eqb(Ins):
    no = 0x27
    def __str__(self):
        return f"eqb r{self.z}, r{self.x}, r{self.y}"

class Neb(Ins):
    no = 0x28
    def __str__(self):
        return f"neb r{self.z}, r{self.x}, r{self.y}"

class Or(Ins):
    no = 0x2a
    def __str__(self):
        return f"or r{self.z}, r{self.x}, r{self.y}"

class Not(Ins):
    no = 0x2d
    def __str__(self):
        return f"not r{self.z}, r{self.x}"

class Jmp(Ins):
    no = 0x30
    def __str__(self):
        return f"jmp {hex(self.v)}"

class Jeq(Ins):
    no = 0x31
    def __str__(self):
        return f"jeq r{self.z}, {hex(self.v)}"

class Jne(Ins):
    no = 0x32
    def __str__(self):
        return f"lne r{self.z}, {hex(self.v)}"

class Declare(Ins):
    no = 0x33
    def __str__(self):
        return f"decl {self.z}, {self.x}"

class Ret(Ins):
    no = 0x34
    def __str__(self):
        return f"ret"

class RetVal(Ins):
    no = 0x35
    def __str__(self):
        return f"ret r{self.x}"

class Call(Ins):
    no = 0x36
    def __str__(self):
        return f"call {hex(self.v)}"

class Copy(Ins):
    no = 0x38
    def __str__(self):
        return f"copy r{self.z}, r{self.x}, r{self.y}"

class New(Ins):
    no = 0x3A
    def __str__(self):
        return f"new r{self.z}, {hex(self.v)}"

class Del(Ins):
    no = 0x3C
    def __str__(self):
        return f"del r{self.z}, {hex(self.v)}"

class Getfield(Ins):
    no = 0x3D
    def __str__(self):
        return f"getfield r{self.z}, {hex(self.v)}"

class Mkarray(Ins):
    no = 0x3E
    def __str__(self):
        return f"mkarray r{self.z}"

class Getindex(Ins):
    no = 0x3F
    def __str__(self):
        return f"getindex r{self.z}, r{self.x}"

class Arrlength(Ins):
    no = 0x40
    def __str__(self):
        return f"arrlength r{self.z}, r{self.x}"

class Delarray(Ins):
    no = 0x41
    def __str__(self):
        return f"delarray r{self.z}"


decoder = InstructionDecoder()
decoder += SetTrue
decoder += SetFalse
decoder += LoadSdataWord
decoder += LoadSdataString
decoder += MovReg
decoder += MovRes
decoder += SetArg
decoder += GetStatic
decoder += DerefLoad
decoder += Sizeof
decoder += DerefStore
decoder += StaticStore
decoder += Addi
decoder += Subi
decoder += Muli
decoder += Divi
decoder += Modi
decoder += Inci
decoder += Negi
decoder += Addf
decoder += Subf
decoder += Mulf
decoder += Divf
decoder += Negf
decoder += Lti
decoder += Nei
decoder += Eqi
decoder += Ltf
decoder += Eqb
decoder += Neb
decoder += Or
decoder += Not
decoder += Jmp
decoder += Jeq
decoder += Jne
decoder += Declare
decoder += Ret
decoder += RetVal
decoder += Call
decoder += Copy
decoder += New
decoder += Del
decoder += Getfield
decoder += Mkarray
decoder += Getindex
decoder += Arrlength
decoder += Delarray

class Code:
    def __init__(self, f):
        self.f = f
        self.off = f.tell()
        while True:
            x = decoder(f)
            print(f"    {x}")
            if isinstance(x, (Ret, RetVal)):
                break

