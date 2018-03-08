import xyaml
import enums
x=[]
x.append(x)
x.append([x])
x[1].append(x[1])
xyaml.save_yaml({
    "xbinver":enums.XBINversion(4),
    "endian":enums.Endian.LITTLE,
    "uid":0x12345678,
    "yamlver":2,
    "data":x})
