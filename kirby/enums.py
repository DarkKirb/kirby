from enum import Enum

class Games(Enum):
    RTDL = "SUK" #Return To Dream Land
    TDX = "BAL" #Triple DeluXe
    KFD = "JVX" #Kirby Fighters Deluxe
    DDD = "JVQ" #Dedede Drum Dash deluxe
    KPR = "AT3" #Kirby Planet Robobot
    TKCD = "JLK" #Team Kirby Clash Deluxe
    KBB = "JHU" #Kirby's Blowout Blast
    KBR = "AJ8" #Kirby Battle Royale
    KSA = "TBA" #To Be Announced

class Console(Enum):
    WII = 0
    _3DS = 1
    SWITCH = 2

class XBINversion(Enum):
    ORIGINAL = 2
    NEW = 4

class Endian(Enum):
    LITTLE = 0
    BIG = 1
    def __str__(self):
        return "little" if self == Endian.LITTLE else "big"

class XBINmagic(Enum):
    RTDL_MAIN = 0xFDE9
    RTDL_MINT = 0x3A4



def get_game_console(game):
    if game == Games.RTDL:
        return Console.WII
    if game == Games.KSA:
        return Console.SWITCH
    return Console._3DS

def get_console_endian(console):
    if console == Console.WII:
        return Endian.BIG
    return Endian.LITTLE

def get_game_endian(game):
    return get_console_endian(get_game_console(game))

def get_game_xbin_ver(game):
    if game in [Games.KBR, Games.KSA]:
        return XBINversion.NEW
    return XBINversion.ORIGINAL
