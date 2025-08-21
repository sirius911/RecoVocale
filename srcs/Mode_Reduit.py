
import tkinter as tk
from pynput.keyboard import Key
from Mode import Mode
from utils_window import create_buttons, update_status_bar
from menus import create_menus
from info import REDUIT, VERSION
from utils_keyboard import Simulator
from Correcteur import intercept, corrige_ponctuation


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
        from mydict_corrector import correct_with_dict
        # --- NOUVEAU : correction via my.dic AVANT intercept() ---
        try:
            if self.app.config.dictionnaire:
                text = correct_with_dict(text)
        except Exception as e:
            # on reste robuste : en cas d'erreur, on n'interrompt pas le flux
            print(f"[mydict_corrector] erreur: {e}")

        # Post-traitements
        txt, inter = intercept(text, self.app.insertions.get())
        while inter:
            txt, inter = intercept(text, self.app.insertions.get())
        txt = corrige_ponctuation(txt)
        # if self.app.config.dictionnaire:
        #     txt = corriger_texte(txt)

        to_copy = f" {txt}" if self.app.config.word_space else f"{txt} "

        def _copy_and_paste():
            # 1) maj presse-papier (thread UI garanti)
            self.root.clipboard_clear()
            self.root.clipboard_append(to_copy)
            self.root.update_idletasks()
            # 2) petit after pour laisser Windows “committer” le clipboard
            self.root.after(0, lambda: Simulator([Key.ctrl, 'v']))
            # 3) log une fois que c’est parti
            self.log(text)

        self.add_to_ui_queue(_copy_and_paste)

    def copy_to_clipboard(self, text: str) -> None:
        pass

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
