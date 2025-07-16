import os
import time
import pygame
import tempfile
from datetime import datetime
import tkinter as tk

from Mode_Direct import Mode_Direct
from utils_window import create_menus, create_buttons
from info import APPRENTI
from sftp_upload import upload_files_to_sftp


class Mode_Apprenti(Mode_Direct):
    """
    Mode d'apprentissage de RecoVocale.

    Ce mode est destiné à entraîner les utilisateurs à relire, corriger et valider
    leurs transcriptions. Il permet de rejouer l'audio, de copier le texte corrigé,
    puis de l’envoyer automatiquement sur un serveur distant via SFTP.

    Il fournit un retour utilisateur clair via des boutons, la lecture audio,
    et une interface restreinte à l’essentiel pour l’apprentissage.
    """
    def __init__(self, app):
        super().__init__(app, APPRENTI)
        self.enter()
        # Répertoire temporaire pour les fichiers
        self.temp_dir = tempfile.gettempdir()  # Utiliser le répertoire temporaire du système
        self.temp_wav_file = os.path.join(self.temp_dir, "temp.wav")
        self.temp_txt_file = os.path.join(self.temp_dir, "temp.txt")
        # self.pile = ['']
        self.ready_to_learn = False
        self.audio_playing = False

    def ui(self) -> None:
        """
        Construit l'interface utilisateur du mode Apprenti, incluant :
        - une zone de texte avec scroll,
        - une barre de statut,
        - le menu et les boutons spécifiques.
        """
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
        self.text_box = tk.Text(self.text_box_frame, yscrollcommand=self.text_box_scrollbar.set, wrap="word")
        self.text_box.pack(fill=tk.BOTH, expand=True)
        # balise pour les mots incorrects
        self.text_box.tag_config("incorrect", foreground="red", underline=True)
        self.text_box.config(state=tk.DISABLED)

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

        create_menus(self)
        create_buttons(self)

    def init_pygame_mixer(self) -> None:
        """
        Initialise `pygame.mixer` et les événements associés à la lecture audio.
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

    def quit_pygame_mixer(self) -> None:
        """
        Ferme proprement `pygame.mixer` si initialisé.
        """

        if pygame.mixer.get_init():
            pygame.mixer.quit()
            print("Pygame mixer fermé proprement.")

    def unpause(self, audio_file=None) -> None:
        """
        Relance le client si l'utilisateur est prêt à apprendre.

        Args:
            audio_file (str | None): Fichier audio à transcrire.
        """
        if not self.ready_to_learn:
            super().unpause(audio_file)

    def stop_client(self) -> None:
        """
        Arrête le client et interrompt la lecture audio si nécessaire.
        """

        if self.audio_playing:
            pygame.mixer.music.stop()
        super().stop_client()

    def clear_text_box(self) -> None:
        """
        Vide la zone de texte, supprime les fichiers temporaires,
        et remet l'interface dans son état initial.
        """

        time.sleep(0.5)
        self.save_text_box()
        self.engine.clear()
        self.text_box.config(state=tk.NORMAL)
        self.text_box.delete('1.0', tk.END)
        self.rec_button.config(state=tk.NORMAL)
        self.learning_button.config(state=tk.DISABLED)
        self.play_button.config(state=tk.DISABLED)
        self.text_box.config(state=tk.DISABLED)
        self.audio_playing = False
        self.ready_to_learn = False

        # Fermer pygame.mixer et effacer les fichiers
        self.quit_pygame_mixer()

        # Effacement des fichiers temporaires
        fichiers = [self.temp_txt_file, self.temp_wav_file]
        for fichier in fichiers:
            if os.path.exists(fichier):
                print(f"Effacement de {fichier}")
                os.remove(fichier)
            else:
                print(f"{fichier} non trouvé")

        self.root.update()

    def start_transcription_loop(self):
        """
        Thread de transcription qui affiche les segments partiels et colle les segments complets.
        """
        super().start_transcription_loop()
        self.ready_to_learn = True
        self.text_box.config(state=tk.NORMAL)
        self.rec_button.config(state=tk.DISABLED)
        self.learning_button.config(state=tk.NORMAL)
        self.play_button.config(state=tk.NORMAL)
        self.trash_button.config(state=tk.NORMAL)

    def learning(self) -> None:
        """
        Enregistre le texte et l'audio temporaire, les envoie par SFTP,
        puis réinitialise l'interface pour une nouvelle session d’apprentissage.
        """

        label_service = "" if self.app.config.service.lower() == "tous" else f"[{self.app.config.service}]"
        transcription = f"{label_service}{self.text_box.get("1.0", tk.END)}"
        self.copy_to_clipboard()
        with open(self.temp_txt_file, "w", encoding="utf-8") as fichier_text:
            fichier_text.write(transcription)
        filename = datetime.now().strftime("%Y%m%d%H%M%S%f")[:-4]

        print(f"On a deux fichiers : \n\t-wav->{self.temp_wav_file} et \n\t-text->{self.temp_txt_file}")
        self.status_bar.config(text="Transfert des fichiers...")
        result, e = upload_files_to_sftp(audio_file=self.temp_wav_file,
                                         text_file=self.temp_txt_file,
                                         filenames=filename)

        self.status_bar.config(text="Merci.")
        time.sleep(1)
        self.clear_text_box()
        self.pile = ['']

        self.log(transcription)

    def check_pygame_events(self) -> None:
        """
        Vérifie les événements pygame (fin de lecture) de façon cyclique.
        """

        if self.monitoring_events:
            for event in pygame.event.get():
                if event.type == self.end_event:
                    self.on_audio_end()

            # Planifier la vérification à nouveau dans 100 ms si la surveillance est active
            self.root.after(100, self.check_pygame_events)

    def on_audio_end(self) -> None:
        """
        Gère la fin de lecture de l’audio : remet les boutons à l’état initial.
        """

        # Remettre l'état des boutons à "play"
        self.audio_playing = False
        self.play_button.config(image=self.play_image)  # Remettre l'image à "play"
        self.status_bar.config(text="Lecture terminée.")

        # Arrêter la surveillance des événements
        self.monitoring_events = False

    def play(self) -> None:
        """
        Lance ou arrête la lecture du fichier audio temporaire selon l’état actuel.
        Gère aussi la reprise depuis la dernière position.
        """

        time.sleep(0.1)
        # Vérifiez si pygame.mixer est initialisé avant de jouer l'audio
        if not pygame.mixer.get_init():
            print("Pygame mixer n'est pas initialisé. Initialisation en cours...")
            self.init_pygame_mixer()
        if self.ready_to_learn:
            if not self.audio_playing:
                # playing
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
