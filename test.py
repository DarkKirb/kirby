from kirby.mint import *
with loader.MintColl("/home/darkkirb/SUKE01/DATA/files/mint/Archive.bin") as f:
    for s in f.strgen():
        print(s)
