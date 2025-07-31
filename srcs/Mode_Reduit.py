
import tkinter as tk
from pynput.keyboard import Key
from Mode import Mode
from utils_window import create_menus, create_buttons, show_bubble_message
from utils_window import remove_bubble, update_status_bar
from info import REDUIT, VERSION
from utils_keyboard import Simulator
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
        remove_bubble
        self.a_ecrit = True
        self.engine.clear_transcriptions()
        self.engine.clear()
        self.shown_segments = set()
        self.running_thread = False

    def update_sortie(self):
        transcription_en_cours, transcription_totale = self.engine.get_reduit()

        # ── partiel ─────────────────────────────────────────
        if not all(c == ' ' for c in transcription_en_cours):
            show_bubble_message(self.root, transcription_en_cours)
            update_status_bar(self.status_bar, "* Transcription ... *",
                              bg="red", fg="darkblue", anchor=tk.CENTER)

        # ── segments complets ──────────────────────────────
        for texte in list(transcription_totale):
            if texte in self.shown_segments or not texte:
                continue
            self.shown_segments.add(texte)

            def traiter_segment(t=texte):
                remove_bubble()

                # post-corrections
                txt, _ = intercept(t, self.app.insertions.get())
                txt = corrige_ponctuation(txt)
                if self.app.config.dictionnaire:
                    txt = corriger_texte(txt)

                # copier-coller au curseur
                self.root.clipboard_clear()
                self.root.clipboard_append(f"{txt} ")
                try:
                    Simulator([Key.ctrl, 'v'])
                except Exception as e:
                    print("[pynput]", e)

                    self.log(text=txt)
            self.add_to_ui_queue(traiter_segment, texte)

            # remove_bubble()
            # self.root.clipboard_clear()
            # text_apres_intercept, _ = intercept(texte, self.app.insertions.get())
            # text_apres_ponctuation = corrige_ponctuation(text_apres_intercept)
            # if self.app.config.dictionnaire:
            #     text_to_copy = corriger_texte(text_apres_ponctuation)
            # else:
            #     text_to_copy = text_apres_ponctuation
            # self.root.clipboard_append(f"{text_to_copy} ")
            # Simulator([Key.ctrl, 'v'])
            # self.log(text=text_to_copy)

        # texte, completed = self.engine.get_reduit()
        # if all(c == " " for c in texte):
        #     return
        # if not completed:
        #     show_bubble_message(self.root, texte)
        #     self.status_bar.config(text="* Transcription ... *",
        #                            bg='lightblue', fg='darkblue', anchor=tk.CENTER)
        #     self.a_ecrit = False
        # else:
        #     if texte and texte not in self.shown_segments:
        #         self.shown_segments.add(texte)
        #         remove_bubble()
        #         self.root.clipboard_clear()
        #         text_apres_intercept, _ = intercept(texte, self.app.insertions.get())
        #         text_apres_ponctuation = corrige_ponctuation(text_apres_intercept)
        #         if self.app.config.dictionnaire:
        #             text_to_copy = corriger_texte(text_apres_ponctuation)
        #         else:
        #             text_to_copy = text_apres_ponctuation
        #         self.root.clipboard_append(f"{text_to_copy} ")
        #         if not self.a_ecrit:
        #             Simulator([Key.ctrl, 'v'])
        #             self.a_ecrit = True
        #             self.log(text=text_to_copy)

    def start_transcription_loop(self):
        super().start_transcription_loop()
        remove_bubble()
        # remove_bubble(self.root)
        # if not self.a_ecrit and text_bulle:
        #     print("icicicicicici")
        #     self.root.clipboard_append(text_bulle)
        #     Simulator([Key.ctrl, 'v'])
        #     self.a_ecrit = True
        #     self.log(text=text_bulle)

        self.running_thread = False
        self.engine.clear()
        self.shown_segments = set()

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
        remove_bubble()
        self.running_thread = False
        if self.engine.is_connected():
            self.engine.stop()
            self.engine.disconnect()
        super().exit()
        return ""
