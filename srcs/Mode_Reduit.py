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

    def enter(self) -> None:
        """
        Initialise l'interface et configure le client de transcription pour le mode Réduit.
        """
        super().enter()
        # self.mode = REDUIT
        # self.mod_var.set(REDUIT)
        self.ui()
        # self.client_manager = None
        self.pile = ['']
        self.a_ecrit = False  # permet de ne pas écrire deux fois si le client stop avant la fin
        # self.repetition = 0
        # self.texte_memoire = ""
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

    # def _update_barre_status(self) -> None:
    #     """
    #     Met à jour le message affiché dans la barre de statut selon l'état de l'application.
    #     """
    #     message = f"RecoVocale {VERSION}"

    #     if not self.engine.is_connected():
    #         self.status_bar.config(text=message, fg='red', bg='lightblue', anchor=tk.W)
    #     elif self.engine.is_capturing():
    #         if self.file_source is not None:
    #             message = f"Transcription de [{self.file_source}] ... en cours"
    #         else:
    #             message = "Transcription en cours..."
    #         self.status_bar.config(text=message, fg='black', bg='red', anchor=tk.CENTER)
    #     elif not self.engine.is_transcription_terminee():
    #         self.status_bar.config(text="Transcription ...en cours", bg='lightblue', fg='darkblue', anchor=tk.W)
    #     else:
    #         self.status_bar.config(text=message, bg='lightblue', fg='darkblue', anchor=tk.W)

    # def pause(self) -> None:
    #     if self.app.recording:
    #         print("Pause() in Mode Réduit")
    #         self.engine.stop()
    #         # self.running_thread = False
    #         self.app.recording = False
    #         self.update()

    # def unpause(self, audio_file=None) -> None:
    #     if not self.app.recording:
    #         print("UnPausing client in Mode Réduit")
    #         self.engine.start()
    #         if not self.engine.is_connected():
    #             if not self.engine.connect():
    #                 print("❌ Impossible de se connecter au serveur WhisperLive via DLL.")
    #                 return
    #         if not self.running_thread:
    #             self.engine.start()
    #             self.thread = threading.Thread(target=self.start_transcription_loop, daemon=True)
    #             self.thread.start()
    #         else:
    #             print(f"non démarrage du threading car running_thread = True, recording = {self.app.recording}")

    #         self.app.recording = True
    #     self.update()
    #     print("sortie de unpause()")

    # def stop_client(self) -> None:
    #     """
    #     Arrête le client de transcription.
    #     """

    #     print("Stop client in Mode Réduit")
    #     self.app.recording = False
    #     self.running_thread = False
    #     if self.thread and self.thread.is_alive():
    #         self.thread.join(timeout=0.5)
    #     self.engine.stop()
    #     self.update()
    #     # super().stop_client()

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

        while True:
            try:
                self.update_reduit()
                if (self.engine.is_transcription_terminee() and self.a_ecrit
                        and not self.app.recording) or not self.running_thread:
                    break

            except Exception as e:
                print(f"[Mode_Reduit] Erreur dans le thread : {e}")
            # time.sleep(0.1)

        print(f"Sortie du thread avec self.app.recording = {self.app.recording}")
        # self.engine.print_transcriptions_lignes()
        self.running_thread = False
        # self.update_reduit()

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

    # def handle_dropped_file(self, file_path: str) -> None:
    #     """
    #     Gère un fichier audio glissé-déposé. Non implémenté dans ce mode.

    #     Args:
    #         file_path (str): Chemin vers le fichier audio.
    #     """

    #     self.status_bar.config(text='Non implémenté', bg='lightblue', fg='darkblue', anchor=tk.W)
    #     # print(f"[Mode_Direct] Traitement du fichier : {file_path}")
    #     # self.unpause(file_path)
