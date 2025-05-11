import re
import string
import time
from Mode import Mode
import tkinter as tk
from utils_window import create_menus, create_buttons, show_bubble_message, remove_bubble, update_bubble_background
from info import REDUIT, VERSION
from ClientManager import ClientManager
from utils_keyboard import Simulator
from pynput.keyboard import Key
from loger import envoyer_log


class Mode_Reduit(Mode):
    def enter(self):
        self.mode = REDUIT
        self.mod_var.set(REDUIT)
        self.ui()
        #----------------- Lien Client Whisper -----------------------
        self.client_manager = ClientManager(
            host = self.app.config.server_ip,
            port = self.app.config.port,
            lang = "fr",
            model = "small",
            translate = False,
            use_vad = True,
            save_output_recording = False,
            output_recording_filename = "",
            update_callback = self.update_transcriptions,  # Pass the callback to ClientManager
            insertions = self.app.insertions,
            fenetre_gestion_insertions = self.is_ouverte,
            mode=self,
            nb_repeat=self.app.config.nb_repeat,
            ip_client=self.app.ip_client,
        )
        
        super().enter()
        self.pile = ['']
        self.a_ecrit = False # permet de ne pas écrire deux fois si le client stop avant la fin
        self.repetition = 0
        self.texte_memoire = ""

    def ui(self): 
        create_menus(self)
        create_buttons(self)

        # Configure the grid system of the root window
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Create the status bar at the bottom of the window
        self.status_bar = tk.Label(self.root, text=f"RecoVocale {VERSION}", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=2, column=0, sticky="ew")

    def pause(self):
        if self.app.recording:
            print("Pausing client in Mode Réduit")
            super().pause()

    def unpause(self, audio_file=None):
        if not self.app.recording:
            print("UnPausing client in Mode Réduit")
            super().unpause(audio_file)

    def stop_client(self):
        print("Stop client in Mode Réduit")
        super().stop_client()

    def stop(self):
        self.stop_client()
        # remove_bubble()
        if not self.a_ecrit:
            self.update_transcriptions(message=self.transcription.text_en_cours, ending=True)
        else:
            Simulator(['\n'])
    def valid_transcriptions(self):
        self.stop_client()

    def update_transcriptions(self, message, ending):
        if message is not None:
            self.transcription.update(message, -1)
        if ending:
            remove_bubble()
            # copie dans clipboard
            self.root.clipboard_clear()
            text_to_copy = ' ' + self.corriger_texte(self.transcription.text_en_cours)

            self.root.clipboard_append(text_to_copy)
            # coller
            if not self.a_ecrit:
                Simulator([Key.ctrl, 'v'])
                self.a_ecrit = True
            self.transcription.validation()
            self.status_bar.config( text=f'RecoVocale {VERSION}', bg='lightblue', fg='darkblue', anchor=tk.W)
            self.repetition = 0
            self.texte_memoire = ""
            envoyer_log("end_transcription", text_to_copy)
            if not self.app.recording:
                self.pause()
                self.status_bar.config( text=f'RecoVocale {VERSION}', bg='lightblue', fg='darkblue', anchor=tk.W)
        else:
            if self.texte_memoire != message:
                self.texte_memoire = message
                self.repetition = 0
            else:
                self.repetition += 1
            if self.repetition >= self.app.config.nb_repeat:
                update_bubble_background("light green")

            show_bubble_message(self.root, message)
            self.status_bar.config(text=f'* Transcription ({self.repetition}) *', bg='lightblue', fg='darkblue', anchor=tk.CENTER)
            self.a_ecrit = False
            
    def corriger_texte(self, texte):
        if not self.app.config.dictionnaire:
            return texte
        # Séparer le contenu en mots
        mots = re.findall(r'\b[\w-]+\b', texte)  # Prend en compte les mots composés avec des traits d'union

        texte_corrige = texte  # Crée une copie du texte original pour les corrections
        offset = 0  # Utilisé pour ajuster les indices après chaque correction

        for mot in mots:
            # Nettoyer le mot de la ponctuation en début et fin, sans modifier l'original
            mot_nettoye = mot.strip(string.punctuation)
            
            # Vérifier chaque mot
            if mot_nettoye and not self.dico.check(mot_nettoye):
                # Obtenir les suggestions
                suggestions = self.dico.suggest(mot_nettoye)

                # Si une seule suggestion est disponible et l'option auto est activée, remplacer automatiquement le mot
                if len(suggestions) == 1:
                    correct_mot = suggestions[0]
                    
                    # Calculer les positions dans le texte corrigé en utilisant l'offset
                    start_idx = texte_corrige.find(mot, offset)
                    end_idx = start_idx + len(mot)
                    
                    # Remplacer le mot incorrect par le mot correct
                    texte_corrige = texte_corrige[:start_idx] + correct_mot + texte_corrige[end_idx:]
                    
                    # Ajuster l'offset pour prendre en compte la différence de longueur
                    offset += len(correct_mot) - len(mot)

        return texte_corrige

    def clear_text_box(self):
        Simulator([Key.delete])

    def undo(self, event=None):
        Simulator([Key.ctrl,"z"])
        
    def exit(self):
        remove_bubble()
        super().exit()
        return self.transcription.get() # on retourne la transcription en cours

    def handle_dropped_file(self, file_path):
        """
        Gère un fichier glissé-déposé en l'envoyant à la transcription.
        """
        print(f"[Mode_Direct] Traitement du fichier : {file_path}")
        self.unpause(file_path)