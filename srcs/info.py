from types import SimpleNamespace

VERSION = "0.61L"

#------------------------ M O D E S ----------------------
BIG = SimpleNamespace()
BIG.name = "BIG"
BIG.resizable = True
BIG.topmost = False
BIG.window_width = 940
BIG.window_height = 709
BIG.button_width = 30
BIG.simule_keyboard = False

SMALL = SimpleNamespace()
SMALL.name = "SMALL"
SMALL.resizable = False
SMALL.topmost = True
SMALL.window_width = 200
SMALL.window_height = 65
SMALL.button_width = 15
SMALL.simule_keyboard = True