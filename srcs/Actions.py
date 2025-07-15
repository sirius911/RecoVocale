import ctypes
import time
import tkinter as tk
import subprocess
from abc import ABC, abstractmethod
from pynput.keyboard import Key
from typing import Optional, List, Union

from utils_keyboard import Simulator, key_display_names


class Action(ABC):
    """
    Classe abstraite de base pour toutes les actions disponibles dans l'application.
    Chaque sous-classe doit implémenter la méthode `execute`.
    """
    def __init__(self, app):
        """
        Args:
            app: Instance principale de l'application à laquelle l'action est liée.
        """
        self.app = app

    @property
    def __name__(self) -> str:
        """Nom de la classe d'action."""
        return self.__class__.__name__

    @abstractmethod
    def execute(self) -> None:
        """Méthode à implémenter par chaque action concrète."""
        pass


class NoAction(Action):
    def execute(self, hascode) -> None:
        print(f"No Action for hascode : {hascode}")


class Pause(Action):
    def execute(self) -> None:
        self.app.pause()


class Unpause(Action):
    def execute(self) -> None:
        # if not self.app.transcription_en_cours:
        self.app.unpause(None)


class ValidTranscriptions(Action):
    def execute(self) -> None:
        self.app.valid_transcriptions()


class StopAction(Action):
    def execute(self) -> None:
        self.app.stop()


class Clear(Action):
    def execute(self) -> None:
        if self.app.status_bar:
            self.app.status_bar.config(text='- Del -', bg='lightblue', fg='darkblue', anchor=tk.CENTER)
        self.app.clear_text_box()


class Toggle_start_stop(Action):
    def execute(self) -> None:
        self.app.toggle_start_stop()


class Keyboard(Action):
    """
    Simule une ou plusieurs frappes clavier.

    Args:
        app: Référence à l'application principale.
        keys (str | list): Les touches à simuler.
        status_bar (bool): Si True, affiche les touches dans la barre de statut.
    """
    def __init__(self, app, keys: Union[str, List[str]] = "", status_bar: bool = True):
        super().__init__(app)
        self.keys = keys
        self.status_bar = status_bar

    def _format_keys(self, data: Union[str, List[str]]) -> str:
        if isinstance(data, list):
            # Si data est une liste, on traite chaque élément individuellement
            return ' + '.join(key_display_names.get(item, str(item)) for item in data)
        else:
            # Sinon, comportement normal
            return self.key_display_names.get(data, data)

    def execute(self, data: Optional[Union[str, List[str]]] = None) -> None:
        if data is None:
            data = self.keys
        if self.status_bar:
            affichage = self._format_keys(data)
            self.app.status_bar.config(text=f'- {affichage} -', bg='lightblue', fg='darkblue', anchor=tk.CENTER)
        Simulator(data=data, debug=False)


class Copie_clipboard(Action):
    def execute(self) -> None:
        self.app.copy_to_clipboard()
        time.sleep(0.5)
        self.app._update_barre_status()


class CopierColler(Action):
    def execute(self) -> None:
        self.app.copy_to_clipboard()
        time.sleep(0.5)
        Simulator([Key.ctrl, 'v'])


class Attendre(Action):
    def __init__(self, app, duree):
        super().__init__(app)
        self.duree = duree

    def execute(self) -> None:
        time.sleep(self.duree)


'''
Partie pour le lancement de commande par des mots clés
Non implémenté dans les interceptions
'''
# Constantes pour les options de fenêtre
SW_SHOWNORMAL = 1
SW_SHOWMINIMIZED = 2
SW_SHOWMAXIMIZED = 3


class Run(Action):
    """
    Lance un exécutable avec des arguments, avec une option de fenêtre (normal, maximized, minimized).

    Args:
        app: Référence à l'application principale.
        executable (str): Chemin de l'exécutable.
        arguments (list[str] | None): Arguments de la ligne de commande.
        window_mode (str): Mode d'affichage de la fenêtre ('normal', 'maximized', 'minimized').
    """
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
