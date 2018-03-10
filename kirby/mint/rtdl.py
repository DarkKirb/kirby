#RTDL specifics
import struct
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
        return f"ld r{self.z}, true"

class SetFalse(Ins):
    no = 0x02
    def __str__(self):
        return f"ld r{self.z}, false"

class LoadSdataWord(Ins):
    no = 0x03
    def __init__(self, f):
        super().__init__(f)
        self.data = int.from_bytes(f.sdata[self.v], str(f.endian))
        self.float_data, = struct.unpack("<f", struct.pack("<I", self.data))
    def __str__(self):
        return f"ld r{self.z}, {hex(self.v)} ({hex(self.data)} or {self.float_data})"

class LoadSdataString(Ins):
    no = 0x04
    def __init__(self, f):
        super().__init__(f)
        namepos = int.from_bytes(f.sdata[self.v], str(f.endian))
        x = f.tell()
        f.seek(namepos)
        namelen = int.from_bytes(f.read(4), str(f.endian))
        self.name = f.read(namelen).decode()
        f.seek(x)
    def __str__(self):
        return f"ld str r{self.z}, {hex(self.v)} (\"{self.name}\")"

class MovReg(Ins):
    no = 0x05
    def __str__(self):
        return f"ld r{self.z}, r{self.x}"

class MovRes(Ins):
    no = 0x06
    def __str__(self):
        return f"ldfz r{self.z}"

class SetArg(Ins):
    no = 0x07
    def __str__(self):
        return f"ldfr [{self.z}], r{self.x}"


class GetStatic(Ins):
    no = 0x09
    def __init__(self, f):
        super().__init__(f)
        self.static = f.xrefs[self.v]
    def __str__(self):
        return f"ld r{self.z}, [{hex(self.v)}] ({self.static})"

class DerefLoad(Ins):
    no = 0x0A
    def __str__(self):
        return f"ld r{self.z}, [r{self.x}]"

class Sizeof(Ins):
    no = 0x0B
    def __str__(self):
        return f"ld r{self.z}, sizeof:{hex(self.v)}"

class DerefStore(Ins):
    no = 0x0C
    def __str__(self):
        return f"st [r{self.z}], r{self.x}"

class StaticStore(Ins):
    no = 0x0D
    def __init__(self, f):
        super().__init__(f)
        self.static = f.xrefs[self.v]
    def __str__(self):
        return f"st [{hex(self.v)}], r{self.z} ({self.static})"

class Addi(Ins):
    no = 0x0E
    def __str__(self):
        return f"addi32 r{self.z}, r{self.x}, r{self.y}"

class Subi(Ins):
    no = 0x0F
    def __str__(self):
        return f"subi32 r{self.z}, r{self.x}, r{self.y}"

class Muli(Ins):
    no = 0x10
    def __str__(self):
        return f"muls32 r{self.z}, r{self.x}, r{self.y}"

class Divi(Ins):
    no = 0x11
    def __str__(self):
        return f"divs32 r{self.z}, r{self.x}, r{self.y}"

class Modi(Ins):
    no = 0x12
    def __str__(self):
        return f"mods32 r{self.z}, r{self.x}, r{self.y}"

class Inci(Ins):
    no = 0x13
    def __str__(self):
        return f"inci32 r{self.z}"

class Deci(Ins):
    no = 0x14
    def __str__(self):
        return f"deci32 r{self.z}"

class Negi(Ins):
    no = 0x15
    def __str__(self):
        return f"negs32 r{self.z}, r{self.x}"

class Addf(Ins):
    no = 0x16
    def __str__(self):
        return f"addf32 r{self.z}, r{self.x}, r{self.y}"

class Subf(Ins):
    no = 0x17
    def __str__(self):
        return f"subf32 r{self.z}, r{self.x}, r{self.y}"

class Mulf(Ins):
    no = 0x18
    def __str__(self):
        return f"mulf32 r{self.z}, r{self.x}, r{self.y}"

class Divf(Ins):
    no = 0x19
    def __str__(self):
        return f"divf32 r{self.z}, r{self.x}, r{self.y}"

class Incf(Ins):
    no = 0x1A
    def __str__(self):
        return f"incf32 r{self.z}"

class Decf(Ins):
    no = 0x1B
    def __str__(self):
        return f"decf32 r{self.z}"

class Negf(Ins):
    no = 0x1c
    def __str__(self):
        return f"negf32 r{self.z}, r{self.x}"

class Lti(Ins):
    no = 0x1d
    def __str__(self):
        return f"lts32 r{self.z}, r{self.x}, r{self.y}"

class Les(Ins):
    no = 0x1e
    def __str__(self):
        return f"les32 r{self.z}, r{self.x}, r{self.y}"

class Eqi(Ins):
    no = 0x1f
    def __str__(self):
        return f"eqi32 r{self.z}, r{self.x}, r{self.y}"

class Nei(Ins):
    no = 0x20
    def __str__(self):
        return f"nei32 r{self.z}, r{self.x}, r{self.y}"

class Ltf(Ins):
    no = 0x21
    def __str__(self):
        return f"ltf32 r{self.z}, r{self.x}, r{self.y}"

class Lef(Ins):
    no = 0x22
    def __str__(self):
        return f"lef32 r{self.z}, r{self.x}, r{self.y}"

class Eqf(Ins):
    no = 0x23
    def __str__(self):
        return f"eqf32 r{self.z}, r{self.x}, r{self.y}"

class Nef(Ins):
    no = 0x24
    def __str__(self):
        return f"nef32 r{self.z}, r{self.x}, r{self.y}"

class Ltcmp(Ins):
    no = 0x25
    def __str__(self):
        return f"ltcmp r{self.z}, r{self.x}"

class Lecmp(Ins):
    no = 0x26
    def __str__(self):
        return f"lecmp r{self.z}, r{self.x}"

class Eqb(Ins):
    no = 0x27
    def __str__(self):
        return f"eqbool r{self.z}, r{self.x}, r{self.y}"

class Neb(Ins):
    no = 0x28
    def __str__(self):
        return f"nebool r{self.z}, r{self.x}, r{self.y}"

class Andi(Ins):
    no = 0x29
    def __str__(self):
        return f"andi32 r{self.z}, r{self.x}, r{self.y}"

class Or(Ins):
    no = 0x2a
    def __str__(self):
        return f"ori32 r{self.z}, r{self.x}, r{self.y}"

class Xor(Ins):
    no = 0x2b
    def __str__(self):
        return f"xori32 r{self.z}, r{self.x}, r{self.y}"

class Nti(Ins):
    no = 0x21
    def __str__(self):
        return f"nti32 r{self.z}, r{self.x}"

class Not(Ins):
    no = 0x2d
    def __str__(self):
        return f"not r{self.z}, r{self.x}"

class Sll(Ins):
    no = 0x2e
    def __str__(self):
        return f"slli32 r{self.z}, r{self.x}, r{self.y}"

class Slr(Ins):
    no = 0x2f
    def __str__(self):
        return f"slr32 r{self.z}, r{self.x}, r{self.y}"

def unsigned_to_signed(x):
    if x >= 0x8000:
        return -0x10000 + x
    return x

class Jmp(Ins):
    no = 0x30
    def __init__(self, f):
        super().__init__(f)
        self.v = unsigned_to_signed(self.v)
    def __str__(self):
        return f"jmp {hex(self.v)}"

class Jeq(Ins):
    no = 0x31
    def __init__(self, f):
        super().__init__(f)
        self.v = unsigned_to_signed(self.v)
    def __str__(self):
        return f"jmppos r{self.z}, {hex(self.v)}"

class Jne(Ins):
    no = 0x32
    def __init__(self, f):
        super().__init__(f)
        self.v = unsigned_to_signed(self.v)
    def __str__(self):
        return f"jmpneg r{self.z}, {hex(self.v)}"

class Declare(Ins):
    no = 0x33
    def __str__(self):
        return f"fenter {self.z}, {self.x}"

class Ret(Ins):
    no = 0x34
    def __str__(self):
        return f"fleave"

class RetVal(Ins):
    no = 0x35
    def __str__(self):
        return f"fret r0"

class Call(Ins):
    no = 0x36
    def __init__(self, f):
        super().__init__(f)
        self.static = f.xrefs[self.v]
    def __str__(self):
        return f"call {hex(self.v)} ({self.static})"

class Yield(Ins):
    no = 0x37
    def __str__(self):
        return f"yield r{self.z}"


class Copy(Ins):
    no = 0x38
    def __str__(self):
        return f"mcopy r{self.z}, r{self.x}, r{self.y}"

class Zero(Ins):
    no = 0x38
    def __str__(self):
        return f"mzeros r{self.z}, r{self.x}"


class New(Ins):
    no = 0x3A
    def __init__(self, f):
        super().__init__(f)
        self.static = f.xrefs[self.v]
    def __str__(self):
        return f"sppsh r{self.z}, {hex(self.v)} ({self.static})"

class Sppshz(Ins):
    no = 0x3B
    def __str__(self):
        return f"sppshz r{self.z}, r{self.x}"

class Del(Ins):
    no = 0x3C
    def __init__(self, f):
        super().__init__(f)
        self.static = f.xrefs[self.v]
    def __str__(self):
        return f"sppop r{self.z}, {hex(self.v)} ({self.static})"

class Getfield(Ins):
    no = 0x3D
    def __init__(self, f):
        super().__init__(f)
        self.static = f.xrefs[self.v]
    def __str__(self):
        return f"addofs r{self.z}, {hex(self.v)} ({self.static})"

class Mkarray(Ins):
    no = 0x3E
    def __str__(self):
        return f"arpshz r{self.z}"

class Getindex(Ins):
    no = 0x3F
    def __str__(self):
        return f"aridx r{self.z}, r{self.x}"

class Arrlength(Ins):
    no = 0x40
    def __str__(self):
        return f"arlen r{self.z}, r{self.x}"

class Delarray(Ins):
    no = 0x41
    def __str__(self):
        return f"arpop r{self.z}"


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
decoder += Deci
decoder += Negi
decoder += Addf
decoder += Subf
decoder += Mulf
decoder += Divf
decoder += Incf
decoder += Decf
decoder += Negf
decoder += Lti
decoder += Les
decoder += Eqi
decoder += Nei
decoder += Ltf
decoder += Lef
decoder += Eqf
decoder += Nef
decoder += Ltcmp
decoder += Lecmp
decoder += Eqb
decoder += Neb
decoder += Andi
decoder += Or
decoder += Xor
decoder += Nti
decoder += Not
decoder += Sll
decoder += Slr
decoder += Jmp
decoder += Jeq
decoder += Jne
decoder += Declare
decoder += Ret
decoder += RetVal
decoder += Call
decoder += Yield
decoder += Copy
decoder += Zero
decoder += New
decoder += Sppshz
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
        insns = {}
        def trace_code():
            while True:
                cur_pos = f.tell() - self.off
                if cur_pos in insns.keys():
                    break
                x = decoder(f) #Read instruction
                insns[cur_pos] = x #add instruction to instruction dict
                #interpret instruction
                if isinstance(x, (Ret, RetVal)): #Return Instruction
                    break
                if isinstance(x, Jmp): #Unconditional jump
                    f.seek(f.tell() + x.v*4)
                if isinstance(x, (Jeq, Jne)): #Conditional jump
                    c = f.tell()
                    trace_code()
                    f.seek(f.tell() + x.v*4)
        trace_code()
        for k in sorted(insns.keys()):
            v = insns[k]
            print(f"{hex(k)}: {v}")
