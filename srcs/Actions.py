import time
import tkinter as tk
import subprocess
from abc import ABC, abstractmethod
from pynput.keyboard import Key
from typing import Optional, List, Union
import os
import ctypes
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


class Run(Action):
    """
    Lance un exécutable avec des arguments, avec une option de fenêtre (normal, maximized, minimized).

    Args:
        app: Référence à l'application principale.
        executable (str): Chemin de l'exécutable.
        arguments (list[str] | None): Arguments de la ligne de commande.
        window_mode (str): Mode d'affichage de la fenêtre ('normal', 'maximized', 'minimized').
    """
    def __init__(self, app, executable, arguments=None, window_mode="normal", verb="open"):
        super().__init__(app)
        self.executable = executable
        self.arguments = arguments if arguments else []
        self.window_mode = window_mode  # "normal", "maximized", "minimized"
        self.verb = verb

    def execute(self):

        target = self.executable
        args = self.arguments or []

        SW_SHOWNORMAL = 1
        SW_SHOWMINIMIZED = 2
        SW_SHOWMAXIMIZED = 3
        show_map = {
            "normal": SW_SHOWNORMAL,
            "minimized": SW_SHOWMINIMIZED,
            "maximized": SW_SHOWMAXIMIZED,
        }
        show_cmd = show_map.get(self.window_mode, SW_SHOWNORMAL)

        ext = os.path.splitext(target)[1].lower()
        is_exe = ext in (".exe", ".com", ".bat", ".cmd")

        if is_exe:
            # Lancement classique (avec gestion du show window)
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = show_cmd
            command = [target] + list(args)
            subprocess.Popen(command, startupinfo=si)
            return

        # Sinon : utiliser ShellExecute (assoc. de fichiers)
        ShellExecuteW = ctypes.windll.Shell32.ShellExecuteW
        verb = self.verb or "open"
        # paramètres passés sous forme de chaîne (peu d'applis de fichier en ont besoin)
        params = " ".join(map(str, args)) if args else None
        # uDir = None (répertoire courant)
        ret = ShellExecuteW(None, verb, target, params, None, show_cmd)
        if ret <= 32:
            raise OSError(f"ShellExecute failed (code {ret}) for {verb} {target!r}")
