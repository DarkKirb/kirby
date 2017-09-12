#!/usr/bin/env python3

import argparse
import os

parser = argparse.ArgumentParser(description="XBIN Archive Manager")

actiongroup = parser.add_mutually_exclusive_group(required=True)
actiongroup.add_argument("-A", "--append", nargs='+')
actiongroup.add_argument("-c", "--create", nargs='+')
actiongroup.add_argument("-d", "--delete", nargs='+')
actiongroup.add_argument("-t", "--test", "--list", nargs='*')
actiongroup.add_argument("-u", "--update", "--replace", nargs='+')
actiongroup.add_argument("-x", "--extract", nargs='*')

parser.add_argument("-f", "--file", required=True)
parser.add_argument("-L", "--little-endian", action="store_true", help="create a little endian file (For TD, PR)")

args = parser.parse_args()
print(args)
endian = "little" if args.little_endian else "big"

class XARReader(object):
    def __init__(self, f):
        self.f=f
        assert f.read(4) == b'XBIN'
        self.endian = 'big' if f.read(2) == b'\x12\x34' else 'little'
        assert f.read(2) == b'\x02\x00'
        self.total_size = int.from_bytes(f.read(4), self.endian)
        f.read(4)
        filecount = int.from_bytes(f.read(4), self.endian)
        files={}
        for i in range(filecount):
            fnameoff = int.from_bytes(f.read(4), self.endian)
            foff = int.from_bytes(f.read(4), self.endian)
            o = f.tell()
            f.seek(fnameoff)
            fnamelen = int.from_bytes(f.read(4), self.endian)
            fname = f.read(fnamelen).decode("UTF-8")
            files[fname]=foff
            f.seek(o)
        self.files=files
    def list(self):
        return list(self.files.keys())
    def read(self, fname):
        if not fname in self.files.keys():
            raise FileNotFoundError("Could not find {} in archive!".format(fname))
        self.f.seek(self.files[fname]+8)
        filesize = int.from_bytes(self.f.read(4), self.endian)
        self.f.seek(self.files[fname])
        return self.f.read(filesize)
def read_all_files(fname):
    with open(fname, "rb") as f:
        ar = XARReader(f)
        files={}
        for fi in ar.list():
            files[fi]=ar.read(fi)

    return files

def write_xar(fname, files):
    with open(fname, "wb") as f:
        f.write(b"XBIN")
        f.write((0x1234).to_bytes(2, endian))
        f.write(b'\x02\0')

        f.write(bytes(4))
        f.write(b'XAR\x1a')

        f.write(len(files.keys()).to_bytes(4, endian))
        offset = 20 + len(files.keys())*8
        wdata=b''
        for fname, data in files.items():
            f.write(offset.to_bytes(4, endian))
            fname=fname.encode("UTF-8")
            owdatalen = len(wdata)
            wdata += len(fname).to_bytes(4, endian)
            wdata += fname
            if len(wdata) % 4:
                wdata += bytes(4-(len(wdata)%4))
            offset += len(wdata)-owdatalen

            f.write(offset.to_bytes(4, endian))
            owdatalen = len(wdata)
            wdata += data
            if len(wdata) % 4:
                wdata += bytes(4-(len(wdata)%4))
            offset += len(wdata) - owdatalen
        f.write(wdata)
        flen=f.tell()
        f.seek(8)
        f.write(flen.to_bytes(4, endian))

if args.test is not None:
    with open(args.file, "rb") as f:
        if args.test == []:
            for fi in XARReader(f).list():
                print(fi)
        else:
            for fi in XARReader(f).list():
                if fi in args.test:
                    print(fi)
elif args.extract is not None:
    with open(args.file, "rb") as f:
        ar = XARReader(f)
        for fi in ar.list():
            if args.extract != [] and fi not in args.extract:
                continue
            os.makedirs(os.path.dirname(fi), exist_ok=True)
            with open(fi, "wb") as f2:
                f2.write(ar.read(fi))
elif args.create is not None:
    files={}
    atemp=args.create[:]
    args.create=[]
    for fname in atemp:
        if not os.path.isdir(fname):
            args.create.append(fname)
        else:
            for root, dirs, fils in os.walk(fname):
                for f in fils:
                    args.create.append(os.path.join(root,f))
    for fname in args.create:
        with open(fname, "rb") as f:
            files[fname]=f.read()

    write_xar(args.file, files)
elif args.append is not None:
    files = read_all_files(args.file)
    atemp = args.append[:]
    args.append=[]
    for fname in atemp:
        if not os.path.isdir(fname):
            args.append.append(fname)
        else:
            for root, dirs, fils in os.walk(fname):
                for f in fils:
                    args.append.append(os.path.join(root,f))
    for fname in args.append:
        with open(fname, "rb") as f:
            files[fname]=f.read()
    write_xar(args.file, files)

elif args.delete is not None:
    files = read_all_files(args.file)
    for f in args.delete:
        if f not in files.keys():
            continue
        del files[f]
    write_xar(args.file, files)
elif args.update is not None:
    files = read_all_files(args.file)
    for fname in args.update:
        with open(fname, "rb") as f:
            files[fname]=f.read()
    write_xar(args.file, files)
