import os
import shutil
import time
from Mode import Mode
import tkinter as tk
from utils_window import create_menus, create_buttons
from info import APPRENTI
from ClientManager import ClientManager
import pygame
from datetime import datetime
import tempfile


class Mode_Apprenti(Mode):
    def enter(self):
        self.mode = APPRENTI
        self.mod_var.set(APPRENTI)
        self.ui()
        # Répertoire temporaire pour les fichiers
        self.temp_dir = tempfile.gettempdir()  # Utiliser le répertoire temporaire du système
        self.temp_wav_file = os.path.join(self.temp_dir, "temp.wav")
        self.temp_txt_file = os.path.join(self.temp_dir, "temp.txt")
        #----------------- Lien Client Whisper -----------------------
        self.client_manager = ClientManager(
            self.app.config.server_ip,
            self.app.config.port,
            "fr",
            "small",
            False,
            True,
            True,
            self.temp_wav_file,
            self.update_transcriptions,  # Pass the callback to ClientManager
            self.app.insertions,
            self.is_ouverte,
        )
        super().enter()
        self.flag_begin = True
        
        self.ready_to_learn = False
        self.audio_playing = False

        # Initialisation de pygame.mixer
        self.init_pygame_mixer()
        # # Initialiser pygame.mixer et pygame.display pour la gestion des événements
        # try:
        #     pygame.mixer.init()
        #     pygame.display.set_mode((1, 1))  # Créer une fenêtre minimaliste pour gérer les événements
        #     print("Pygame mixer et affichage initialisés.")
        # except pygame.error as e:
        #     print(f"Erreur d'initialisation de pygame : {e}")
        # self.pos_lecture = 0 # position de lecture
        #  # Configurer l'événement de fin de lecture audio
        # self.end_event = pygame.USEREVENT + 1
        # pygame.mixer.music.set_endevent(self.end_event)
        # self.monitoring_events = False  # Flag pour savoir si on surveille les événements pygame


    def ui(self):
       

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
        self.text_box = tk.Text(self.text_box_frame, yscrollcommand=self.text_box_scrollbar.set)
        self.text_box.pack(fill=tk.BOTH, expand=True)

        # Configure the selection tag
        self.text_box.tag_configure("sel", background="yellow", foreground="black")

        # Attach the scrollbar to the text box
        self.text_box_scrollbar.config(command=self.text_box.yview)

        # Attacher l'événement à la Text box
        self.text_box.bind("<KeyRelease>", self.on_text_change)

        # Create the status bar at the bottom of the window
        self.status_bar = tk.Label(self.root, text="Bienvenue dans l'application", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=2, column=0, sticky="ew")

        create_menus(self)
        create_buttons(self)

    def init_pygame_mixer(self):
        """
        Initialise pygame.mixer et configure les événements pour la gestion audio.
        """
        try:
            if not pygame.mixer.get_init():  # Ne pas réinitialiser si déjà initialisé
                pygame.mixer.init()
                pygame.display.set_mode((1, 1))  # Créer une petite fenêtre pour les événements
                print("Pygame mixer et affichage initialisés.")
            # Configurer l'événement de fin de lecture audio
            self.pos_lecture = 0
            self.end_event = pygame.USEREVENT + 1
            pygame.mixer.music.set_endevent(self.end_event)
            self.monitoring_events = False
        except pygame.error as e:
            print(f"Erreur d'initialisation de pygame : {e}") 

    def quit_pygame_mixer(self):
        """
        Ferme proprement pygame.mixer.
        """
        if pygame.mixer.get_init():
            pygame.mixer.quit()
            print("Pygame mixer fermé proprement.")

    def pause(self):
        time.sleep(0.1)
        if self.app.config.debug:
            print("Pausing client in Mode Direct")
        super().pause()

    def unpause(self):
        time.sleep(0.1)
        if self.app.config.debug:
            print(f"UnPausing client in Mode Direct")
        if not self.ready_to_learn:
            super().unpause()

    def stop_client(self):
        if self.app.config.debug:
            print(f"Stop client in Mode Direct")
        if self.audio_playing:
            pygame.mixer.music.stop()
        super().stop_client()


    def stop(self):
        self.stop_client()

    def valid_transcriptions(self):
        self.stop_client()

    def copy_to_clipboard(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self .get_selected_text()[0])

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
        # text_to_del, all = self.get_selected_text()
        # self.valid_transcriptions()
       
        # if all:
        self.transcription.clear()
        self.text_box.delete('1.0', tk.END)
        self.rec_button.config(state=tk.NORMAL)
        self.learning_button.config(state=tk.DISABLED)
        self.play_button.config(state=tk.DISABLED)
        self.audio_playing = False
        self.ready_to_learn = False
        
        # Fermer pygame.mixer et effacer les fichiers
        self.quit_pygame_mixer()

        # Effacement des fichiers temporaires
        fichiers = [self.temp_txt_file, self.temp_wav_file]
        for fichier in fichiers:
            if os.path.exists(fichier):
                print(f"Effacement de {self.temp_wav_file}")
                os.remove(fichier)
            else:
                print(f"{self.temp_wav_file} non trouvé")

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

    def on_text_change(self, event):
        self.transcription.text_box = self.text_box.get("1.0", tk.END)
        self.transcription.pos_cur = self.get_pos_curseur()

    def update_transcriptions(self, message, ending):
        if self.flag_begin:
            self.flag_begin = False
            self.transcription.pos_cur = self.get_pos_curseur()
            self.transcription.cur_selec = self.get_pos_select()

        self.transcription.update(message)

        self.text_box.delete('1.0', tk.END)
        self.text_box.insert(tk.END, self.transcription.text_box_en_cours)
        if ending:
            self.flag_begin = True
            self.transcription.validation()
            self.set_pos_curseur(self.transcription.fin_insertion)
            self.ready_to_learn = True
            self.rec_button.config(state=tk.DISABLED)
            self.learning_button.config(state=tk.NORMAL)
            self.play_button.config(state=tk.NORMAL)
        else:
            self.set_pos_curseur(self.transcription.pos_cur)

    def learning(self):
        transcription = self.text_box.get("1.0", tk.END)
        with open(self.temp_txt_file, "w", encoding="utf-8") as fichier_text:
            fichier_text.write(transcription)
        filename = datetime.now().strftime("%Y%m%d%H%M%S%f")[:-4]

        #####   Les fichiers devrons etre transférér dans un serveur de stockage
        print(f"On a deux fichiers : \n\t-{filename}.txt et \n\t-{filename}.wav")
        # Chemin de destination
        destination_dir = r"C:\Users\lorcyr\data"  # Répertoire de destination
        # Définir les nouveaux noms de fichiers dans le répertoire de destination
        new_txt_file = os.path.join(destination_dir, f"{filename}.txt")
        new_wav_file = os.path.join(destination_dir, f"{filename}.wav")
        # Liste des fichiers à copier avec les nouveaux noms
        fichiers = [(self.temp_txt_file, new_txt_file), (self.temp_wav_file, new_wav_file)]
        # Copier chaque fichier dans le répertoire de destination avec le nouveau nom
        for fichier_src, fichier_dest in fichiers:
            if os.path.exists(fichier_src):
                try:
                    shutil.copy(fichier_src, fichier_dest)
                    print(f"Fichier {fichier_src} copié sous le nom {fichier_dest}")
                except Exception as e:
                    print(f"Erreur lors de la copie du fichier {fichier_src} : {e}")
            else:
                print(f"Le fichier {fichier_src} n'existe pas.")
        self.status_bar.config(text="Merci.")
        time.sleep(1)
        self.clear_text_box()

    def check_pygame_events(self):
        """
        Vérifie périodiquement les événements pygame seulement lorsqu'on surveille les événements.
        """
        if self.monitoring_events:
            for event in pygame.event.get():
                if event.type == self.end_event:
                    self.on_audio_end()

            # Planifier la vérification à nouveau dans 100 ms si la surveillance est active
            self.root.after(100, self.check_pygame_events)

    def on_audio_end(self):
        """
        Appelé lorsque la lecture audio est terminée.
        """
        # Remettre l'état des boutons à "play"
        self.audio_playing = False
        self.play_button.config(image=self.play_image)  # Remettre l'image à "play"
        self.status_bar.config(text="Lecture terminée.")
        
        # Arrêter la surveillance des événements
        self.monitoring_events = False
       
    def play(self):
        time.sleep(0.1)
        # Vérifiez si pygame.mixer est initialisé avant de jouer l'audio
        if not pygame.mixer.get_init():
            print("Pygame mixer n'est pas initialisé. Initialisation en cours...")
            self.init_pygame_mixer()
        if self.ready_to_learn:
            if not self.audio_playing:
                #playing
                try:
                    if self.pos_lecture > 0:
                        # on reprend la lecture
                        pygame.mixer.music.play(start=self.pos_lecture)
                    else:
                        # Charger le fichier 
                        print(f"Ouverture de {self.temp_wav_file}")
                        pygame.mixer.music.load(self.temp_wav_file)
                        pygame.mixer.music.play()
                    
                    self.play_button.config(image=self.pause_image)
                    self.play_button.config(text="Stop Audio")
                    self.status_bar.config(text="Lecture en cours...")
                    self.audio_playing = True
                    # Démarrer la surveillance des événements pygame
                    if not self.monitoring_events:
                        self.monitoring_events = True
                        self.check_pygame_events()  # Commencer la surveillance

                except pygame.error as e:
                    print(f"Impossible de lire le fichier audio: {e}")
            else:
                # Mettre en pause, et enregistrer la position actuelle
                self.pos_lecture = pygame.mixer.music.get_pos() / 1000.0  # Obtenir la position en secondes
                pygame.mixer.music.stop()
                self.play_button.config(text="Play Audio")
                self.play_button.config(image=self.play_image)
                self.status_bar.config(text="Lecture arrêtée.")
                self.audio_playing = False

    def exit(self):
        retour = self.text_box.get("1.0", tk.END) # on retourne la transcription en cours
        super().exit()
        return retour