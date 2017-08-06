import struct
from PIL import Image
roomMetadata=0x38B1
levelTilesets=0x2070
tileTable=0x20A2
f=open("kdl.gb","rb")

def rom2gb(off):
    if off < 0x4000:
        return (0,off)
    off-=0x4000
    bank = off // 0x4000
    boff = off % 0x4000
    return (bank, boff+0x4000)
def gb2rom(bank, off):
    if off < 0x4000:
        return off
    return bank * 0x4000 + off - 0x4000
vram=[0]*0x10000
vram[0x97C0:0x97D0]=[255]*16 #basic colors
vram[0x97D0:0x97E0]=[0,255]*8
vram[0x97E0:0x97F0]=[255,0]*8
vram[0x97F0:0x9800]=[0]*16
chars=[]
def readRoomMeta(level, room):
    f.seek(roomMetadata+level*2)
    off=struct.unpack("<H", f.read(2))[0]
    f.seek(off+room*8)
    bank,pos,width,height = struct.unpack(">BHBB",f.read(5))
    return {"bank":bank, "pos":pos, "width":width, "height":height, "off":gb2rom(bank,pos)}
def loadTileset(level):
    global chars
    f.seek(levelTilesets+level*5)
    bank,hl = struct.unpack(">BH",f.read(3))
    de = struct.unpack("<H",f.read(2))[0] #Why is it mixing endians?!?!
    f.seek(gb2rom(bank,hl))
    data=decompress()
    #Copy it to the VRAM buffer
    off = de
    for i in range(len(data)):
        vram[off+i]=data[i]
    f.seek(tileTable+level*3)
    f.seek(gb2rom(*struct.unpack(">BH",f.read(3))))
    chars=decompress()
    chars+=bytes(0x800-len(chars))
def decompress():
    data=[]
    usages=[0,0,0,0,0,0,0]
    while True:
        input = f.read(1)[0]
        if input == 0xFF:
            break
        if (input & 0xE0) == 0xE0:
            command = (input >> 2) & 0x7
            length = (((input &3)<<8) | (f.read(1)[0]))+1
        else:
            command = input >> 5
            length = (input & 0x1F) + 1
        if ((command == 2) and (len(data)+2*length > 65535)) or (len(data)+length > 65535):
            raise ValueError("Compressed data is too big")
        usages[command]+=1
        if command == 0:
            for c in f.read(length):
                data.append(c)
        elif command == 1:
            d = f.read(1)[0]
            for i in range(length):
                data.append(d)
        elif command == 2:
            d,e = f.read(2)
            for i in range(length):
                data.append(d)
                data.append(e)
        elif command == 3:
            d = f.read(1)[0]
            for i in range(length):
                def lim(x):
                    return x & 0xFF
                data.append(lim(d+i))
        elif command == 4:
            off = struct.unpack(">H",f.read(2))[0]
            if len(data) < off:
                raise ValueError("This isn't a backref, but a frontref")
            for i in range(length):
                data.append(data[off+i])
        elif command == 5:
            off = struct.unpack(">H",f.read(2))[0]
            def bitrotate(x):
                y=0
                if  x& 0x80:
                    y|=0x01
                if  x& 0x40:
                    y|=0x02
                if  x& 0x20:
                    y|=0x04
                if  x& 0x10:
                    y|=0x08
                if  x& 0x08:
                    y|=0x10
                if  x& 0x04:
                    y|=0x20
                if  x& 0x02:
                    y|=0x40
                if  x& 0x01:
                    y|=0x80
                return y
            if len(data) < off:
                raise ValueError("This isn't a backref, but a frontref")
            for i in range(length):
                data.append(bitrotate(data[off+i]))
        elif command == 6:
            off=struct.unpack(">H",f.read(2))[0]
#            print(hex(off),length)
            if len(data) < off:
                raise ValueError("This isn't a backref, but a frontref")
#            if off-length < 0:
#                raise ValueError("Cannot backref over the beginning of decompressed data!")
            for i in range(length):
                data.append(data[off-i])
        else:
            raise ValueError("Unknown method {}".format(command))
    print(usages)
    return data
def plotCHR(im, tile, x, y):
    #Tile is based around 0x8800. For values > 0x80, it starts at 0x8800. For the other tiles it begins at 0x9000
    if tile < 0x80:
        off = 0x9000 + tile*16
    else:
        off = 0x8800 + (tile-0x80)*16
#    print("{}->{}".format(hex(tile),hex(off)))
    for xb in range(8):
        for yb in range(8):
            pos = off + yb*2
            color = 2 if vram[pos+1] & (1<<(7-xb)) else 0
            color |= 1 if vram[pos]  & (1<<(7-xb)) else 0
            color = 4 - color
            data=((x*8+xb, y*8+yb), color << 6)
            im.putpixel(*data)
def saveRoom(level, rom, leveltileset=None):
    room = readRoomMeta(level, rom)
    if leveltileset is None:
        loadTileset(level)
    else:
        loadTileset(leveltileset)
    im = Image.new("L", (room["width"]*16, room["height"]*16))
    f.seek(room["off"])
    ldat = decompress()
    for x in range(room["width"]):
        for y in range(room["height"]):
            l=ldat[x+y*room["width"]]
            plotCHR(im, chars[l*4],x*2,y*2)
            plotCHR(im, chars[l*4+1],x*2+1,y*2)
            plotCHR(im, chars[l*4+2],x*2,y*2+1)
            plotCHR(im, chars[l*4+3],x*2+1,y*2+1)
    im.save("level{}-room{}.png".format(level,rom))
for i in range(5):
    saveRoom(0,i)
for i in range(16):
    saveRoom(1,i)
for i in range(8):
    saveRoom(2,i)
for i in range(10):
    saveRoom(3,i)
saveRoom(4,0)
saveRoom(4,1,0)
saveRoom(4,2,1)
saveRoom(4,3,2)
saveRoom(4,4,3)
saveRoom(4,5)
