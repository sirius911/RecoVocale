from utils_keyboard import Simulator
import tkinter as tk


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
    def execute(self, data):
        Simulator(data=data, debug=False)

class Copie_clipboard(Action):
    def execute(self):
        self.app.copy_to_clipboard()

class Selection(Action):
    def execute(self, dir):
        print(f"je dois selectionner")
        self.app.select_text_box(dir)
        
        # selected_text = box.get(tk.SEL_FIRST, tk.SEL_LAST)
        # print(selected_text)
