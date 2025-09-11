
import tkinter as tk
from pynput.keyboard import Key
from Mode import Mode
# import threading
from utils_window import create_buttons, update_status_bar
from menus import create_menus
from info import REDUIT, VERSION
from utils_keyboard import Simulator
# from utils import set_clipboard_plain
# from keyboard_helper import paste_then_nudge_plaintext, sendinput_sequence, build_combo, VK_RETURN
from clipboard import set_clipboard


# _typing_lock = threading.Lock()


# def paste_multiline_with_enters(text: str, soft_break: bool = False, delay: float = 0.01):
#     """
#     Firefox (éditeur Word-like) :
#       - split exact en conservant les vides
#       - lignes non vides: clipboard + Ctrl+Shift+V + nudge
#       - lignes vides: juste le saut
#     """
#     from keyboard_helper import (
#         paste_then_nudge_plaintext, sendinput_sequence, build_combo, VK_RETURN
#     )

#     # 1) ne PAS strip — on veut préserver les lignes vides en tête/fin
#     # 2) normaliser pour splitter et conserver vides
#     parts = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')

#     for i, line in enumerate(parts):
#         is_last = (i == len(parts) - 1)

#         if line:  # ligne non vide -> coller + nudge
#             set_clipboard_plain(line)
#             paste_then_nudge_plaintext(delay=delay)

#         # Si ce n'est pas la dernière "part", on ajoute un saut (même si la ligne était vide)
#         if not is_last:
#             if soft_break:
#                 # Shift+Enter (retour doux)
#                 sendinput_sequence(build_combo(VK_RETURN, shift=True), delay=delay)
#             else:
#                 # Enter (paragraphe)
#                 sendinput_sequence([(VK_RETURN, "tap")], delay=delay)


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

    def unpause(self, audio_file=None):
        if self.app.recording or self.vt.is_recording or not self.app.status_server:
            return
        try:
            self.vt.start()
            self.app.recording = True
            self.on_record_start()
        except Exception as e:
            update_status_bar(status_bar=self.status_bar,
                              text=f"Erreur start micro: {e}", bg="lightblue", fg="darkblue", anchor=tk.W)

    def pause(self):
        if not self.app.recording and not self.vt.is_recording:
            return

        try:
            texte = self.vt.stop()  # transcription finale
        except Exception as e:
            update_status_bar(status_bar=self.status_bar,
                              text=f"Erreur stop/transcription: {e}", bg="lightblue", fg="darkblue", anchor=tk.W)
            texte = ""
        finally:
            self.app.recording = False

        if texte and texte.strip():
            self.handle_final_text(texte)
        self._update_rec_circle()
        self._update_image_button()
        update_status_bar(status_bar=self.status_bar,
                          text="Transcription terminée",
                          bg='lightblue', fg='darkblue', anchor=tk.W)

    def stop(self):
        if self.vt.is_recording or self.app.recording:
            self.pause()
            return
        # sinon: rien de spécial

    def on_record_start(self):
        # UI rouge pendant l'enregistrement
        self._update_rec_circle()
        self._update_image_button()
        update_status_bar(status_bar=self.status_bar,
                          text="* Enregistrement… *",
                          bg="red", fg="darkblue", anchor=tk.CENTER)

    def handle_final_text(self, text: str):

        txt = super().handle_final_text(text)

        to_copy = f" {txt}" if self.app.config.word_space else f"{txt} "

        if not self.is_ouverte():
            set_clipboard(text=to_copy)
            self.root.after(150, lambda: Simulator([Key.ctrl, 'v']))

    def copy_to_clipboard(self) -> None:
        def _copy():
            update_status_bar(status_bar=self.status_bar,
                              text="- Ctrl+C -",
                              bg='lightblue', fg='darkblue', anchor=tk.CENTER)
            self.root.after(0, lambda: Simulator([Key.ctrl, 'c']))
        self.add_to_ui_queue(_copy)

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
        super().exit()
        return ""

    def toggle_word_space(self) -> None:
        """
        Ajoute un espace avant le segment envoyé au curseur
        """

        # maj de la variable config
        self.app.config.word_space = self.word_space_var.get()
