from utils_keyboard import Simulator

class Action:
    def __init__(self, app):
        self.app = app

    def execute(self):
        pass

class NoAction(Action):
    def execute(self):
        print("No Action")

class Pause(Action):
    def execute(self):
        self.app.pause()

class Unpause(Action):
    def execute(self):
        self.app.unpause()

class ValidTranscriptions(Action):
    def execute(self):
        self.app.valid_transcriptions()

class Keyboard(Action):
    def execute(self, text):
        Simulator(text=text, debug=False)
