import os
import time
import pygame
import tempfile
from datetime import datetime
import tkinter as tk

from Mode import Mode
from utils_window import create_menus, create_buttons
from info import APPRENTI
from ClientManager import ClientManager
from sftp_upload import upload_files_to_sftp


class Mode_Apprenti(Mode):
    """
    Mode d'apprentissage de RecoVocale.

    Ce mode est destiné à entraîner les utilisateurs à relire, corriger et valider
    leurs transcriptions. Il permet de rejouer l'audio, de copier le texte corrigé,
    puis de l’envoyer automatiquement sur un serveur distant via SFTP.

    Il fournit un retour utilisateur clair via des boutons, la lecture audio,
    et une interface restreinte à l’essentiel pour l’apprentissage.
    """

    def enter(self) -> None:
        """
        Initialise l'interface et le client Whisper, prépare les chemins
        de fichiers temporaires et configure les éléments nécessaires à l'apprentissage.
        """

        self.mode = APPRENTI
        self.mod_var.set(APPRENTI)
        self.ui()
        # Répertoire temporaire pour les fichiers
        self.temp_dir = tempfile.gettempdir()  # Utiliser le répertoire temporaire du système
        self.temp_wav_file = os.path.join(self.temp_dir, "temp.wav")
        self.temp_txt_file = os.path.join(self.temp_dir, "temp.txt")
        # ----------------- Lien Client Whisper -----------------------
        self.client_manager = ClientManager(
            host=self.app.config.server_ip,
            port=self.app.config.port,
            lang="fr",
            translate=False,
            use_vad=True,
            save_output_recording=True,
            output_recording_filename=self.temp_wav_file,
            update_callback=self.update_transcriptions,  # Pass the callback to ClientManager
            insertions=self.app.insertions,
            fenetre_gestion_insertions=self.is_ouverte,
            mode=self,
            nb_repeat=self.app.config.nb_repeat,
            ip_client=self.app.ip_client,
        )
        super().enter()
        self.pile = ['']

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

    def pause(self) -> None:
        """
        Met le client en pause avec un léger délai pour éviter les conflits.
        """

        time.sleep(0.1)
        if self.app.config.debug:
            print("Pausing client in Mode Direct")
        super().pause()

    def unpause(self, audio_file=None) -> None:
        """
        Relance le client si l'utilisateur est prêt à apprendre.

        Args:
            audio_file (str | None): Fichier audio à transcrire.
        """

        time.sleep(0.1)
        if self.app.config.debug:
            print("UnPausing client in Mode Direct")
        if not self.ready_to_learn:
            super().unpause(audio_file)

    def stop_client(self) -> None:
        """
        Arrête le client et interrompt la lecture audio si nécessaire.
        """

        if self.app.config.debug:
            print("Stop client in Mode Direct")
        if self.audio_playing:
            pygame.mixer.music.stop()
        super().stop_client()

    def stop(self) -> None:
        """
        Stoppe la transcription, réactive les boutons, valide le texte
        et relance la vérification orthographique.
        """

        self.stop_client()
        self.text_box.config(state=tk.NORMAL)
        self.trash_button.config(state=tk.NORMAL)
        self.rec_button.config(state=tk.NORMAL)
        self.transcription_en_cours = False
        self.transcription.validation()
        self.set_pos_curseur(self.transcription.fin_insertion)
        self.status_bar.config(text="Transcription ...interrompue", bg='lightblue', fg='darkblue', anchor=tk.W)
        self.verification_dico(True)

    def valid_transcriptions(self) -> None:
        """
        Valide la transcription actuelle (alias de `stop_client`).
        """
        self.stop_client()

    def copy_to_clipboard(self) -> None:
        """
        Copie le texte sélectionné (ou entier) dans le presse-papier.
        """

        self.status_bar.config(text='- Copie -', bg='lightblue', fg='darkblue', anchor=tk.CENTER)
        self.root.clipboard_clear()
        self.root.clipboard_append(self.get_selected_text()[0])
        time.sleep(0.5)
        self._update_barre_status()

    def get_selected_text(self) -> tuple[str, bool]:
        """
        Récupère le texte sélectionné dans la zone de texte.

        Returns:
            tuple[str, bool]: Le texte et un booléen indiquant si tout le texte est retourné.
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

    def get_pos_select(self) -> tuple[int, int]:
        """
        Récupère les positions globales de la sélection texte.

        Returns:
            tuple[int, int]: (start, end) ou (0, 0) si rien sélectionné.
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

    def clear_text_box(self) -> None:
        """
        Vide la zone de texte, supprime les fichiers temporaires,
        et remet l'interface dans son état initial.
        """

        time.sleep(0.5)
        self.save_text_box()
        self.transcription.clear()
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

    def get_pos_curseur(self) -> int:
        """
        Donne la position actuelle du curseur dans la zone de texte.

        Returns:
            int: Position globale en caractères.
        """

        # Utiliser "1.0" comme point de départ et obtenir le nombre total de caractères jusqu'au curseur
        position_globale = self.text_box.count("1.0", "insert", "chars")
        if position_globale:
            return position_globale[0]
        return 0

    def set_pos_curseur(self, position_globale: int) -> None:
        """
        Replace le curseur à une position donnée.

        Args:
            position_globale (int): Position en caractères depuis le début.
        """

        # Utiliser "1.0" comme point de départ et déplacer le curseur à la position globale
        index_ligne_colonne = self.text_box.index(f"1.0 + {position_globale}c")

        # Repositionner le curseur à l'index ligne.colonne calculé
        self.text_box.mark_set("insert", index_ligne_colonne)

        # S'assurer que le curseur est visible
        self.text_box.see("insert")

    def update_transcriptions(self, message: str, ending: bool) -> None:
        """
        Met à jour le contenu de la transcription affiché à l’écran.

        Args:
            message (str): Nouveau texte à insérer.
            ending (bool): True si la phrase est terminée.
        """

        if not hasattr(self, "text_box") or not self.text_box.winfo_exists():
            return  # Le widget a été détruit
        if message is not None:
            if not self.transcription_en_cours:
                self.trash_button.config(state=tk.DISABLED)
                self.transcription_en_cours = True
                self.transcription.pos_cur = self.get_pos_curseur()
                self.transcription.cur_selec = self.get_pos_select()
                self.save_text_box()

            self.transcription.update(message)
            self.text_box.config(state=tk.NORMAL)
            self.text_box.delete('1.0', tk.END)
            self.text_box.insert(tk.END, self.transcription.text_box_en_cours)
        if ending:
            self.text_box.config(state=tk.NORMAL)
            self.transcription_en_cours = False
            self.transcription.validation()
            self.set_pos_curseur(self.transcription.fin_insertion)
            self.ready_to_learn = True

            self.verification_dico(True)
            if not self.app.recording:
                self.rec_button.config(state=tk.DISABLED)
                self.learning_button.config(state=tk.NORMAL)
                self.play_button.config(state=tk.NORMAL)
                self.trash_button.config(state=tk.NORMAL)
                self.status_bar.config(text="Transcription ...Terminée", bg='lightblue', fg='darkblue', anchor=tk.W)
                self.log(text=self.transcription.text_box_en_cours)
                self.pause()
        else:
            self.text_box.config(state=tk.DISABLED)
            self.set_pos_curseur(self.transcription.pos_cur)

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
        log_text = f"Learning : {"ok" if result else "echec : {e}"}"
        self.log(log_text)

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

    def exit(self) -> str:
        """
        Ferme le mode Apprenti et retourne le texte transcrit en cours.

        Returns:
            str: Texte affiché dans la zone de transcription.
        """

        retour = self.text_box.get("1.0", tk.END)  # on retourne la transcription en cours
        super().exit()
        return retour

    def handle_dropped_file(self, file_path: str) -> None:
        """
        Gère un fichier glissé-déposé (non implémenté dans ce mode).

        Args:
            file_path (str): Chemin vers le fichier audio.
        """

        self.status_bar.config(text='Non implémenté', bg='lightblue', fg='darkblue', anchor=tk.W)
        # print(f"[Mode_Direct] Traitement du fichier : {file_path}")
        # self.unpause(file_path)
