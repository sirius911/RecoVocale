import ctypes
import time
from utils_keyboard import Simulator
import tkinter as tk
import subprocess
from abc import ABC, abstractmethod
from pynput.keyboard import Key


class Action(ABC):
    def __init__(self, app):
        self.app = app

    @abstractmethod
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
        if not self.app.transcription_en_cours:
            self.app.unpause()

class ValidTranscriptions(Action):
    def execute(self):
        self.app.valid_transcriptions()

class Clear(Action):
    def execute(self):
        self.app.clear_text_box()

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

class CopierColler(Action):
    def execute(self):
        self.app.copy_to_clipboard()
        time.sleep(0.5)
        Simulator([Key.ctrl, 'v'])

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

# Constantes pour les options de fenêtre
SW_SHOWNORMAL = 1
SW_SHOWMINIMIZED = 2
SW_SHOWMAXIMIZED = 3
class Run(Action):
    def __init__(self, app, executable, arguments=None, window_mode="normal"):
        super().__init__(app)
        self.executable = executable
        self.arguments = arguments if arguments else []
        self.window_mode = window_mode  # "normal", "maximized", "minimized"

    def execute(self):
        try:
            # Crée la commande avec l'exécutable et les arguments
            command = [self.executable] + self.arguments
            print(f"Exécution de : {' '.join(command)}")
            
            # Crée un processus pour ouvrir l'application sans console supplémentaire
            process = subprocess.Popen(command)

            # Utilise ctypes pour ajuster l'état de la fenêtre
            if self.window_mode == "normal":
                ctypes.windll.user32.ShowWindow(process._handle, SW_SHOWNORMAL)
            elif self.window_mode == "maximized":
                ctypes.windll.user32.ShowWindow(process._handle, SW_SHOWMAXIMIZED)
            elif self.window_mode == "minimized":
                ctypes.windll.user32.ShowWindow(process._handle, SW_SHOWMINIMIZED)
            else:
                raise ValueError("Mode de fenêtre non valide")

        except subprocess.CalledProcessError as e:
            # Si une erreur se produit lors de l'exécution, affiche un message d'erreur
            print(f"Erreur lors de l'exécution de : {self.executable}")
            print(e)
