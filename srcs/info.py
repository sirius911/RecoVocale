from enum import Enum, auto

SERVEUR_IP = "10.1.11.215"
PORT = 9090
VERSION = "0.5"
SHORTCUT = "F3"

BUTTON_WIDTH_BIG = 30
BUTTON_WIDTH_SMALL = 15

class ModeStyle(Enum):
    BIG =    auto()
    SMALL =  auto()
    REDUIT = auto()