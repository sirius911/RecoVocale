from types import SimpleNamespace

VERSION = "0.7"

#------------------------ M O D E S ----------------------
DIRECT = SimpleNamespace()
DIRECT.name = "DIRECT"
DIRECT.resizable = True
DIRECT.topmost = True
DIRECT.window_width = 940
DIRECT.window_height = 709
DIRECT.button_width = 30
DIRECT.simule_keyboard = False

RECORD = SimpleNamespace()
RECORD.name = "RECORD"
RECORD.resizable = True
RECORD.topmost = False
RECORD.window_width = 940
RECORD.window_height = 709
RECORD.button_width = 30
RECORD.simule_keyboard = False

REDUIT = SimpleNamespace()
REDUIT.name = "REDUIT"
REDUIT.resizable = False
REDUIT.topmost = True
REDUIT.window_width = 138
REDUIT.window_height = 60
REDUIT.button_width = 15
REDUIT.simule_keyboard = True