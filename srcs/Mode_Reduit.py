
import tkinter as tk
from pynput.keyboard import Key
from Mode import Mode
from utils_window import create_menus, create_buttons, show_bubble_message, remove_bubble
from info import REDUIT, VERSION
from utils_keyboard import Simulator
# from RecoVocaleClientEngine import RecoVocaleClientEngine
from Correcteur import intercept, corrige_ponctuation, corriger_texte


class Mode_Reduit(Mode):
    """
    Mode de transcription simplifié sans interface utilisateur complète.

    Dans ce mode, l'utilisateur parle et la transcription est automatiquement envoyée
    au presse-papier et collée dans l'application cible, sans intervention manuelle. (Peut être forcé)

    Hérite de la classe `Mode`.
    """
    def __init__(self, app, mode=REDUIT):
        super().__init__(app, mode)
        self.enter()
        self.a_ecrit = False
        self.shown_segments = set()

    def ui(self) -> None:
        """
        Crée l'interface minimale du mode Réduit : menus, boutons, et barre de statut.
        """

        create_menus(self)
        create_buttons(self)

        # Configure the grid system of the root window
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Create the status bar at the bottom of the window
        self.status_bar = tk.Label(self.root, text=f"RecoVocale {VERSION}", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=2, column=0, sticky="ew")

    def stop(self) -> None:
        """
        Arrête la transcription et, si besoin, colle le texte automatiquement.
        """
        print("Stop dans Mode Reduit")
        self.stop_client()
        remove_bubble()
        self.a_ecrit = True
        self.engine.clear_transcriptions()
        self.engine.clear()
        self.running_thread = False

    def update_sortie(self):
        texte, completed = self.engine.get_reduit()
        if not completed:
            show_bubble_message(self.root, texte)
            self.status_bar.config(text="* Transcription ... *",
                                   bg='lightblue', fg='darkblue', anchor=tk.CENTER)
            self.a_ecrit = False
        else:
            if texte and texte not in self.shown_segments:
                self.shown_segments.add(texte)
                remove_bubble()
                self.root.clipboard_clear()
                text_apres_intercept, _ = intercept(texte, self.app.insertions.get())
                text_apres_ponctuation = corrige_ponctuation(text_apres_intercept)
                if self.app.config.dictionnaire:
                    text_to_copy = corriger_texte(text_apres_ponctuation)
                else:
                    text_to_copy = text_apres_ponctuation
                self.root.clipboard_append(text_to_copy)
                if not self.a_ecrit:
                    Simulator([Key.ctrl, 'v'])
                    self.a_ecrit = True
                    self.log(text=text_to_copy)

    def start_transcription_loop(self):
        super().start_transcription_loop()
        text_bulle = remove_bubble()
        if not self.a_ecrit and text_bulle:
            self.root.clipboard_append(text_bulle)
            Simulator([Key.ctrl, 'v'])
            self.a_ecrit = True
            self.log(text=text_bulle)

        self.running_thread = False
        self.engine.clear()

    def clear_text_box(self) -> None:
        """
        Supprime le texte actif en simulant une pression sur la touche Suppr.
        """

        Simulator([Key.delete])

    def undo(self, event=None) -> None:
        """
        Simule Ctrl+Z pour annuler la dernière action dans l'application cible.
        """
        Simulator([Key.ctrl, "z"])

    def exit(self) -> str:
        remove_bubble()
        self.running_thread = False
        if self.engine.is_connected():
            self.engine.stop()
            self.engine.disconnect()
        super().exit()
        return ""
