import time
from Mode import Mode
import tkinter as tk
from utils_window import create_menus, create_buttons
from info import DIRECT
from ClientManager import ClientManager
from utils_keyboard import Simulator
from pynput.keyboard import Key


class Mode_Direct(Mode):
    def enter(self):
        self.mode = DIRECT
        self.mod_var.set(DIRECT)
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
            # mode=self.mode,
            mode=self,
            nb_repeat=self.app.config.nb_repeat,
            ip_client=self.app.ip_client,
            listen=self.app.config.play_audio,
        )
        super().enter()
        self.pile = ['']
        self.transcription_interrompue = False

    def ui(self):
        create_menus(self)
        create_buttons(self)

         # Configure the grid system of the root window
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Create the text box frame
        self.text_box_frame = tk.Frame(self.root)
        self.text_box_frame.grid(row=1, column=0, sticky="nsew")

        # Add scrollbar to the text box
        self.text_box_scrollbar = tk.Scrollbar(self.text_box_frame)
        self.text_box_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Add the text box
        self.text_box = tk.Text(self.text_box_frame, yscrollcommand=self.text_box_scrollbar.set, wrap='word')
        self.text_box.pack(fill=tk.BOTH, expand=True)
        #balise pour les mots incorrects
        self.text_box.tag_config("incorrect", foreground="red", underline=True)
        # self.text_box.config(state=tk.DISABLED)

        # Configure the selection tag
        self.text_box.tag_configure("sel", background="yellow", foreground="black")

        # Attach the scrollbar to the text box
        self.text_box_scrollbar.config(command=self.text_box.yview)

        # Attacher l'événement à la Text box
        self.text_box.bind("<Key>", self.on_text_change)

        self.text_box.bind("<Button-3>", self.show_context_menu)
        # Création du menu contextuel
        self.context_menu = tk.Menu(self.root, tearoff=0)

        # Create the status bar at the bottom of the window
        self.status_bar = tk.Label(self.root, text="Bienvenue dans l'application", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=2, column=0, sticky="ew")

    def pause(self):
        print("Pausing client in Mode Direct")
        super().pause()

    def unpause(self, audio_file=None):
        print(f"UnPausing client in Mode Direct")
        # self.transcription_interrompue = False
        super().unpause(audio_file)

    def stop_client(self):
        print(f"Stop client in Mode Direct")
        super().stop_client()

    def stop(self):
        self.stop_client()
        #essais------------------------
        # si le bouton stop est demandé
        self.text_box.config(state=tk.NORMAL)
        self.trash_button.config(state=tk.NORMAL)
        self.rec_button.config(state=tk.NORMAL)
        self.transcription_en_cours = False
        self.transcription.validation()
        self.set_pos_curseur(self.transcription.fin_insertion)
        self.status_bar.config(text="Transcription ...interrompue", bg='lightblue', fg='darkblue', anchor=tk.W)
        self.transcription_interrompue = True
        self.verification_dico(True)
        #essais------------------------

    def valid_transcriptions(self):
        self.stop_client()

    def get_selected_text(self):
        """
            renvoi le texte selectionné de la TextBox + Flag
            Si aucune selection renvoi toute le text
            le Flag est True si on envoi l'integralité et False si une partie
        """
        try:
            # Vérifie s'il y a une sélection
            if self.text_box.tag_ranges("sel"):
                # Récupère le texte sélectionné
                selected_text = self.text_box.get(tk.SEL_FIRST, tk.SEL_LAST)
                return selected_text, False
            else:
                # si aucune selection on envoi la transcription complète
                return self.transcription.get(), True
        except tk.TclError:
            # Gestion d'erreur si aucune sélection n'est faite
            return self.transcription.get(), True
        
    def get_pos_select(self):
        """
            retourne un couple (start,end) si selection dans text_box ou None 
        """
        try:
            if self.text_box.tag_ranges("sel"):
                # Obtenir les positions 'ligne.colonne' de la sélection
                start = self.text_box.index(tk.SEL_FIRST)
                end = self.text_box.index(tk.SEL_LAST)
                
                # Convertir ces positions en indices globaux
                start_index = self.text_box.count("1.0", start)[0]  # Distance depuis le début du texte
                end_index = self.text_box.count("1.0", end)[0]      # Distance jusqu'à la fin du texte sélectionné
                
                return (start_index, end_index)
            else:
                return (0, 0)
        except tk.TclError:
            return (0, 0)

    def clear_text_box(self):
        """
        Clear the content of the text box.
        """
        time.sleep(0.5)
        self.save_text_box()
        _, all = self.get_selected_text()
        self.valid_transcriptions()
       
        if all:
            self.transcription.clear()
            self.text_box.delete('1.0', tk.END)
        else:
            Simulator([Key.delete])

        self.root.update()

    def get_pos_curseur(self):
        # Utiliser "1.0" comme point de départ et obtenir le nombre total de caractères jusqu'au curseur
        position_globale = self.text_box.count("1.0", "insert", "chars")
        if position_globale:
            return position_globale[0]
        return 0

    def set_pos_curseur(self, position_globale):
        # Utiliser "1.0" comme point de départ et déplacer le curseur à la position globale
        index_ligne_colonne = self.text_box.index(f"1.0 + {position_globale}c")
        
        # Repositionner le curseur à l'index ligne.colonne calculé
        self.text_box.mark_set("insert", index_ligne_colonne)
        
        # S'assurer que le curseur est visible
        self.text_box.see("insert")
    
    def update_transcriptions(self, message, ending):
        if message is not None and not self.transcription_interrompue:
            if not self.transcription_en_cours:
                self.transcription_en_cours = True
                self.trash_button.config(state=tk.DISABLED)
                self.rec_button.config(state=tk.DISABLED)
                self.transcription.pos_cur = self.get_pos_curseur()
                self.transcription.cur_selec = self.get_pos_select()
                self.save_text_box()

            self.transcription.update(message)
            self.text_box.config(state=tk.NORMAL)
            self.text_box.delete('1.0', tk.END)
            self.text_box.insert(tk.END, self.transcription.text_box_en_cours)
        if ending:
            self.text_box.config(state=tk.NORMAL)
            self.trash_button.config(state=tk.NORMAL)
            self.rec_button.config(state=tk.NORMAL)
            self.transcription_en_cours = False
            self.transcription.validation()
            self.set_pos_curseur(self.transcription.fin_insertion)
            self.status_bar.config(text="Transcription ...Terminée", bg='lightblue', fg='darkblue', anchor=tk.W)
            self.verification_dico(True)
            self.pause()
        else:
            self.text_box.config(state=tk.DISABLED)
            self.set_pos_curseur(self.transcription.pos_cur)

    def copy_to_clipboard(self):
        self.status_bar.config(text='- Copie -', bg='lightblue', fg='darkblue', anchor=tk.CENTER)
        self.root.clipboard_clear()
        self.root.clipboard_append(self.get_selected_text()[0])
        time.sleep(0.5)
        self._update_barre_status()

    def exit(self):
        retour = self.text_box.get("1.0", tk.END) # on retourne la transcription en cours
        super().exit()
        return retour
    
    def handle_dropped_file(self, file_path):
        """
        Gère un fichier glissé-déposé en l'envoyant à la transcription.
        """
        print(f"[Mode_Direct] Traitement du fichier : {file_path}")
        self.unpause(file_path)
