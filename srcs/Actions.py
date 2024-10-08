import time
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
    def __init__(self, app, keys="", status_bar=True):
        super().__init__(app)
        self.keys = keys
        self.status_bar = status_bar
    def execute(self, data=None):
        if data is None:
            data = self.keys
        if self.status_bar:
            self.app.status_bar.config(text=f'-{data} -', bg='lightblue', fg='darkblue', anchor=tk.CENTER)
        Simulator(data=data, debug=False)

class Copie_clipboard(Action):
    def execute(self):
        self.app.copy_to_clipboard()
        time.sleep(0.5)
        self.app._update_barre_status()

class Selection(Action):
    def execute(self, dir):
        # print(f"je dois selectionner")
        self.app.select_text_box(dir)
        
        # selected_text = box.get(tk.SEL_FIRST, tk.SEL_LAST)
        # print(selected_text)

class Attendre(Action):
    def __init__(self, app, duree):
        super().__init__(app)
        self.duree = duree

    def execute(self):
        time.sleep(self.duree)

class run(Action):
    def execute(self, executable, arguments):
        print(f"Execution de :{executable} {arguments}")
        #TODO : lance l'executable executable avec les arguments