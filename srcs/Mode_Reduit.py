import time
import tkinter as tk
from pynput.keyboard import Key

# import time
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

    def update_reduit(self):
        self.engine._update()
        partial = self.engine.transcription_en_cours
        if self.engine.transcription_totale:
            complete = list(self.engine.transcription_totale.keys())[-1]
        else:
            complete = ""

        if partial:
            show_bubble_message(self.root, partial)
            self.status_bar.config(text="* Transcription ... *",
                                   bg='lightblue', fg='darkblue', anchor=tk.CENTER)
            self.a_ecrit = False

        if complete and complete not in self.shown_segments:
            self.shown_segments.add(complete)
            remove_bubble()
            self.root.clipboard_clear()
            text_apres_intercept, _ = intercept(complete, self.app.insertions.get())
            text_apres_ponctuation = corrige_ponctuation(f" {text_apres_intercept}")
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
        """
        Thread de transcription qui affiche les segments partiels et colle les segments complets.
        """
        self.running_thread = True
        temps_attente_debut = None

        while True:
            try:
                self.app.recording = self.engine.is_capturing()
                self.update_reduit()

                pas_enregistrement = not self.app.recording
                pret_a_sortir = pas_enregistrement or not self.running_thread

                if pret_a_sortir:
                    if not self.running_thread:
                        break
                    else:
                        if temps_attente_debut is None:
                            temps_attente_debut = time.time()
                        elif time.time() - temps_attente_debut > 3:
                            print("[Mode_Reduit] Plus de 3 secondes sans activité, arrêt du thread.")
                            break
                else:
                    # on réinitialise le timer si on n’est plus dans l’état "quasi-fin"
                    temps_attente_debut = None
            except Exception as e:
                print(f"[Mode_Reduit] Erreur dans le thread : {e}")

        # print(f"Sortie du thread avec self.app.recording = {self.app.recording}\n"
        #       f"et is_transcription_terminée = {self.engine.is_transcription_terminee()}\n"
        #       f"a_ecrit = {self.a_ecrit}\n")
        start = time.time()
        while not self.engine.is_transcription_terminee():

            self.status_bar.config(text='transcription...',
                                   bg='lightblue', fg='darkblue', anchor=tk.CENTER)
            self.engine._update()
            if (time.time()-start) > 1.5:
                print("Timeout dans le thread de transcription, on sort")
                break
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

