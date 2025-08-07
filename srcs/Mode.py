import re
import string
import threading
import time
from tkinter import filedialog
import enchant
import tkinter as tk

from info import REDUIT, VERSION, APPRENTI
from Transcription import Transcription
from insertions import FenetreGestion
from utils_socket import check_server_status
from RecoVocaleClientEngine import RecoVocaleClientEngine
from loger import envoyer_log
from vlc_perso import VLC
from queue_manager import UI_QUEUE
from utils_window import remove_bubble, update_status_bar, show_messagebox


class Mode:
    """
    Classe de base représentant un mode d’utilisation de l'application RecoVocale.

    Elle encapsule la logique d’affichage, de transcription, de gestion du statut,
    du dictionnaire, et d'interactions utilisateur partagées par tous les modes
    (Direct, Apprenti, Réduit).

    Attributes:
        app: Référence à l'application principale.
        root: Fenêtre principale Tkinter.
        transcription: Objet de gestion de la transcription.
        dico: Dictionnaire orthographique enchant.
        fenetre_gestion_ouverte: Indique si la fenêtre des insertions est affichée.
        transcription_en_cours: Booléen indiquant si une transcription est en cours.
        file_source: Fichier audio en cours de transcription (si applicable).
        model: Nom du modèle utilisé pour la transcription.
    """

    def __init__(self, app, mode):
        """
        Initialise le mode avec la fenêtre principale, le dictionnaire,
        et configure les propriétés visuelles.

        Args:
            app: Instance de l'application principale.
        """
        self.root = app.root
        self.app = app
        self.mode = mode
        self.mod_var = tk.StringVar()
        self.mod_var.set(mode)
        self.transcription = Transcription()
        self.fenetre_gestion_ouverte = False  # Attribut pour savoir si la fenêtre est ouverte
        self.transcription_en_cours = False
        self.file_source = None  # peut etre un fichier audio
        # # Définir le chemin du répertoire de configuration dans %APPDATA%\RecoVocale
        self.dico = enchant.Dict("fr_FR")
        self.mots_personnels = set()
        self.model = ""
        self.engine = RecoVocaleClientEngine(ip=self.app.config.server_ip,
                                             port=int(self.app.config.port),
                                             ip_client=self.app.ip_client)
        self.pile = ['']
        self.thread = None
        self.running_thread = False
        self.transcription_interrompue = False
        # self.audio_file = None # redondant
        self.use_vlc = False
        self.vlc = None

        self.pending_tasks = set()  # a supprimer apres les debug

    def enter(self) -> None:
        """
        Applique les propriétés visuelles du mode à la fenêtre principale (taille, titre, topmost).
        """

        self.root.resizable(self.mode.resizable, self.mode.resizable)
        self.root.attributes("-topmost", self.mode.topmost)
        self.root.geometry(f"{self.mode.window_width}x{self.mode.window_height}+" +
                           f"{self.app.config.x_window}+{self.app.config.y_window}")
        if self.mode == REDUIT:
            self.root.title(f"RV v{VERSION}")
        else:
            self.root.title(f"RecoVocale [{self.app.config.server_ip}:{self.app.config.port}] " +
                            f"(v{VERSION}) {"" if self.app.status_server else "not"} connected")

        self.ui()

    def get_selected_text(self):
        return self.transcription.get()

    def stop_client(self) -> None:
        """
        Arrête le client de transcription.
        """
        self.app.recording = False
        self.running_thread = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=0.5)
        self.engine.stop()
        self.update()

    def copy_to_clipboard(self) -> None:
        """
        Copie le contenu de la transcription dans le presse-papier système.
        """
        def copy():
            self.root.clipboard_clear()
            self.root.clipboard_append(self.transcription.get())
            update_status_bar(self.status_bar,
                              text='- Copie -', bg='lightblue', fg='darkblue', anchor=tk.CENTER)
        self.add_to_ui_queue(copy)

    def pause(self) -> None:
        """
        Met en pause la transcription et met à jour.
        """
        print(f"Pause() dans {self.mode.name}")
        if not self.app.recording:
            return

        remove_bubble(force=True)

        if self.use_vlc:
            threading.Thread(target=self.vlc.play_pause(), daemon=True).start()

        else:
            self.engine.stop(self.file_source)
            self.file_source = None  # On ne charge qu'une seule fois

        self.app.recording = False
        self.running_thread = False
        self.update()

    def unpause(self, audio_file: str | None = None):
        """Relance (ou démarre) la boucle de transcription.

        ‣ Si `self.use_vlc` est vrai, on part du principe que `lancer_vlc()`
        a déjà …
            • démarré le serveur pipe (`start_audio_pipe()`),  
            • lancé VLC avec le média choisi et la sortie `--sout` correcte.
        `unpause()` ne fait donc qu’assurer que tout tourne
        et basculer VLC en lecture si besoin.

        ‣ Si l’on n’utilise pas VLC, on garde le comportement précédent :
        `audio_file` désigne alors le fichier à capturer directement.
        """

        # ------------------------------------------------------------
        # 1)  Ne rien faire si l’enregistrement est déjà actif
        # ------------------------------------------------------------
        if self.app.recording:           # déjà en capture
            return

        self.transcription_interrompue = False

        # ------------------------------------------------------------
        # 2)  Connexion à la DLL WhisperLive
        # ------------------------------------------------------------
        if not self.engine.is_connected() and not self.engine.connect():
            update_status_bar(self.status_bar,
                              text="Impossible de se connecter au serveur WhisperLive via DLL.",
                              bg="lightblue", fg="darkblue", anchor=tk.W,
                              )
            print("❌ Impossible de se connecter au serveur WhisperLive via DLL.")
            return

        # ------------------------------------------------------------
        # 3)  Branche « APPRENTI »
        # ------------------------------------------------------------
        if self.mode == APPRENTI:
            self.engine.start(file_temp=self.temp_wav_file)

        # ------------------------------------------------------------
        # 4)  Branche lecture via VLC
        # ------------------------------------------------------------
        elif self.use_vlc:
            update_status_bar(self.status_bar, text="Lecture via VLC", bg="lightblue",
                              fg="darkblue", anchor=tk.CENTER)

            # 4-a  S’assurer que le serveur pipe tourne
            if not self.engine.pipe:           # pipe absent (None ou False)
                self.engine.start_audio_pipe()

            # 4-b  Vérifier que VLC est lancé par « Lancer VLC »
            if self.vlc is None:
                if audio_file is None:
                    show_messagebox(
                        message_type="warning",
                        title="VLC non lancé pour lire",
                        message="Utilisez d’abord le menu « Lancer VLC » pour choisir un fichier."
                    )
                    return

            # 4-c  Remet VLC en lecture seulement s’il est en pause
            if self.vlc is not None:
                self.vlc.play_pause()

        # ------------------------------------------------------------
        # 5)  Capture directe sans VLC
        # ------------------------------------------------------------
        else:
            self.vlc = None
            self.engine.start(file_to_capture=audio_file,
                              listen=self.app.config.play_audio)

        # ------------------------------------------------------------
        # 6)  Attendre le début de la capture audio
        # ------------------------------------------------------------
        for _ in range(20):                # ~1 s max
            if self.engine.is_capturing():
                break
            time.sleep(0.05)

        # ------------------------------------------------------------
        # 7)  Lancer le thread de transcription
        # ------------------------------------------------------------
        self.app.recording = True
        self.thread = threading.Thread(
            target=self.start_transcription_loop, daemon=True
        )
        self.thread.start()

        self.update()

    def exit_app(self) -> None:
        """
        Ferme correctement l'application en appelant la méthode de fermeture principale.
        """

        # self.icon.stop()
        self.app.on_closing()

    def _update_rec_circle(self) -> None:
        """
        Met à jour l'indicateur visuel d'enregistrement (rond rouge/gris).
        """

        fill = 'red' if self.app.recording and self.app.status_server is True else 'grey'
        self.rec_canvas.itemconfig(self.rec_circle, fill=fill)

    def _update_image_button(self) -> None:
        """
        Met à jour l’image du bouton enregistrement/pause et son état (activé/désactivé).
        """

        if self.app.recording:
            self.rec_button.config(image=self.pause_image)
        else:
            self.rec_button.config(image=self.record_image)
        if self.app.status_server is False:
            self.rec_button.config(state=tk.DISABLED)
            self.app.status_server = check_server_status(self.app.config.server_ip,
                                                         self.app.config.port,
                                                         self.app.ip_client)

    def _update_barre_status(self) -> None:
        """
        Met à jour le message affiché dans la barre de statut selon l'état de l'application.
        """
        if self.mode == REDUIT:
            message = f"RecoVocale {VERSION}"
        else:
            message = (
                f"RecoVocale [{self.app.config.server_ip}:{self.app.config.port}] (v{VERSION}) "
                f"{'connected' if self.app.status_server else 'not connected'} "
                f"[{self.app.config.service}]"
            )

        if self.app.status_server is False:
            update_status_bar(self.status_bar, message, 'red', 'lightblue', tk.W)
        elif self.app.recording:
            if self.file_source is not None:
                message = f"{'Transcription via VLC' if self.use_vlc else 'Transcription de'} "
                f"[{self.file_source}] ... en cours"
            else:
                message = "Transcription Entrée audio en cours..."
            update_status_bar(self.status_bar, text=message, fg='black', bg='red', anchor=tk.CENTER)
        elif self.transcription_en_cours:
            update_status_bar(self.status_bar, text="Transcription ...en cours",
                              bg='lightblue', fg='darkblue', anchor=tk.W)
        else:
            update_status_bar(self.status_bar, text=message, bg='lightblue', fg='darkblue', anchor=tk.W)

    def _update_title_window(self) -> None:
        """
        Met à jour le titre de la fenêtre principale avec les infos du mode, serveur et version.
        """

        if self.mode == REDUIT:
            self.root.title(f"RV v{VERSION}")
        else:
            self.root.title(
                f"RecoVocale [{self.app.config.server_ip}:{self.app.config.port}] "
                f"(v{VERSION}) {'connected' if self.app.status_server else 'not connected'} "
                f"[{self.app.config.service}]"
            )

    def start_transcription_loop(self):
        """
        Thread de transcription qui affiche les segments partiels et colle les segments complets.
        """
        print("start_transcription loop au niveau de Mode Class Mere")
        self.running_thread = True
        self.save_text_box()
        while True:
            self.app.recording = self.engine.is_capturing()
            try:

                self.update_sortie()
                if (self.engine.is_transcription_terminee() and not self.app.recording) or not self.running_thread:
                    break

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[Mode_Direct] Erreur dans le thread : {e}")

            time.sleep(0.1)

        self.update_sortie()
        start = time.time()
        while not self.engine.is_transcription_terminee():
            update_status_bar(self.status_bar, text='Attente fin de transcription...',
                              bg='lightblue', fg='darkblue', anchor=tk.W)
            self.update_sortie()
            if (time.time()-start) > 2.0:
                break
        if self.engine.is_transcription_terminee():
            texte_info = "Transcription terminée"
        else:
            texte_info = "Transcription interrompue, on sort"
        update_status_bar(self.status_bar, text=texte_info,
                          bg='lightblue', fg='darkblue', anchor=tk.W)

        print(texte_info)
        print(f"{self.engine.lib.is_task_completed()} and not {self.engine.lib.is_task_in_progress()} => "
              f"{self.engine.lib.is_task_completed() and not self.engine.lib.is_task_in_progress()}")
        self.running_thread = False

    def update(self) -> None:
        """
        Met à jour tous les composants de l'interface (statut, bouton, cercle, titre...).
        """
        def update_safe():
            self._update_rec_circle()
            self._update_image_button()
            self._update_barre_status()
            self._update_title_window()
            if self.app.config.debug:
                self.app.info()
        self.add_to_ui_queue(update_safe)

    def name(self) -> str:
        """
        Retourne le nom du mode actif.

        Returns:
            str: Nom du mode.
        """

        return self.mode.name

    def undo(self, event=None):
        if event and event.keysym in ("Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R"):
            return
        if self.pile:
            dernier_etat = self.pile.pop()
            self.text_box.config(state=tk.NORMAL)
            self.text_box.delete('1.0', tk.END)
            self.text_box.insert('1.0', dernier_etat)
            self.transcription.set(dernier_etat)
            if self.engine:
                self.engine.set(dernier_etat)

        if not self.pile:
            self.pile = ['']
            self.edit_menu.entryconfig(0, state='disabled')

    def toggle_start_stop(self) -> None:
        """
        Lance ou interrompt la transcription en fonction de l'état actuel.
        """

        if self.app.recording:
            self.pause()
        else:
            self.unpause(None)

    def toggle_debug(self) -> None:
        """
        Affiche ou masque la fenêtre de débogage selon l’état de la case à cocher.
        """

        # maj de la variable config
        self.app.config.debug = self.debug_var.get()
        if self.app.config.debug:
            self.app.console_debug.debug_window.deiconify()
        else:
            self.app.console_debug.debug_window.withdraw()

    def toggle_dictionnaire(self) -> None:
        """
        Active ou désactive l’usage du dictionnaire pour la vérification orthographique.
        """

        # maj de la variable config
        self.app.config.dictionnaire = self.dico_var.get()
        if hasattr(self, "text_box") and self.text_box.winfo_exists():
            self.verification_dico()

    def lance_vlc(self):
        """Ouvre une boîte de dialogue pour choisir un média, puis lance VLC déjà
        configuré pour sortir sur le pipe et commence la lecture."""

        self.use_vlc = True
        self.vlc_var.set(True)    # ← coche la case du menu

        # 1) Sélection du fichier
        filepath = filedialog.askopenfilename(
            title="Choisir un fichier audio ou vidéo",
            filetypes=[
                ("Audio/vidéo", "*.wav *.mp3 *.flac *.mp4 *.mkv *.avi *.mov"),
                ("Tous les fichiers", "*.*"),
            ],
        )
        if not filepath:
            return  # l’utilisateur a annulé

        # 2) Démarre d’abord le serveur pipe (indispensable avant VLC)
        if not self.engine.pipe:
            self.engine.start_audio_pipe()

        # 3) (Re)démarre VLC avec le bon --sout et le média choisi
        if self.vlc is not None:
            self.vlc.close()          # on termine proprement le précédent processus
            time.sleep(0.2)

        update_status_bar(self.status_bar, text=f"Chargement via VLC [{filepath}] ... en cours",
                          bg='lightblue', fg='darkblue', anchor=tk.W)
        self.vlc = VLC()
        if not self.vlc.open(filepath):
            print("Impossible de lancer VLC pour ce fichier.")
            return

        time.sleep(0.5)               # petite marge pour négocier le Named Pipe
        self.file_source = filepath

    def toggle_vlc(self, *_):
        """Active ou désactive l’utilisation de VLC."""
        self.use_vlc = self.vlc_var.get()
        if not self.use_vlc and self.vlc is not None:
            self.vlc.close()
            if self.engine:
                self.engine.stop_audio_pipe()

    def exit(self) -> None:
        """
        Détruit tous les widgets enfants de la fenêtre principale.
        """
        if self.use_vlc:
            print("fermeture de vlc")
            if self.vlc is not None:
                self.vlc.close()
        for widget in self.root.winfo_children():
            widget.destroy()

    def ouvrir_gestion_insertions(self) -> None:
        """
        Ouvre la fenêtre de gestion des insertions si elle n’est pas déjà ouverte.
        """

        if not self.fenetre_gestion_ouverte:
            self.fenetre_gestion = FenetreGestion(self.root, self.app.insertions, self.fermer_gestion_insertions)
            self.fenetre_gestion.protocol("WM_DELETE_WINDOW", self.fermer_gestion_insertions)
            self.fenetre_gestion_ouverte = True

    def fermer_gestion_insertions(self) -> None:
        """
        Ferme la fenêtre de gestion des insertions et met à jour son état.
        """

        if self.fenetre_gestion:
            self.fenetre_gestion.destroy()
        self.fenetre_gestion_ouverte = False

    def save_text_box(self) -> None:
        pass

    # def on_text_change(self, event) -> None:
    #     """
    #     Gère les changements dans le champ texte. Ignore certaines touches de contrôle.

    #     Args:
    #         event: Événement clavier de Tkinter.
    #     """

    #     if event and (event.keysym in ("Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R") or
    #                   (event.state & 0x4 and event.keysym == "z")):
    #         return
    #     self.save_text_box()
    #     self.root.after_idle(self.text_change)  # pour attendre que tkinter est bien écrit les modifications

    # def text_change(self) -> None:
    #     """
    #     Applique les changements de texte et met à jour la transcription et le curseur.
    #     """

    #     self.trash_button.config(state=tk.NORMAL)
    #     nouveau_text = self.text_box.get("1.0", tk.END)
    #     # self.save_text_box()
    #     if self.engine:
    #         self.engine.set(nouveau_text)

    #     self.verification_dico()

    def verification_dico(self, auto: bool = False) -> None:
        """
        Vérifie chaque mot du texte via le dictionnaire et marque les erreurs.

        Args:
            auto (bool): Si True, remplace automatiquement les mots mal orthographiés
            quand une seule suggestion est trouvée.
        """
        def verify():
            # efface les marquages précédents
            self.text_box.tag_remove("incorrect", "1.0", tk.END)
            if not self.app.config.dictionnaire:
                return

            contenu = self.text_box.get("1.0", tk.END)
            # Séparer le contenu en mots
            # mots = contenu.split()
            mots = re.findall(r'\b[\w-]+\b', contenu)  # permet de ne pas couper si mot composé (-)

            for mot in mots:
                # Nettoyer le mot de la ponctuation en début et fin, sans modifier l'original
                mot_nettoye = mot.strip(string.punctuation)
                # Vérifier chaque mot
                if mot_nettoye and not self.dico.check(mot_nettoye):
                    # Obtenir les suggestions
                    suggestions = self.dico.suggest(mot_nettoye)

                    # Si une seule suggestion est disponible, remplacer automatiquement le mot
                    if len(suggestions) == 1 and auto:
                        correct_mot = suggestions[0]
                        self.save_text_box()
                        # Trouver la position exacte du mot dans le Text widget
                        start_idx = self.text_box.search(mot, "1.0", tk.END)
                        if not start_idx:
                            continue
                        end_idx = f"{start_idx} + {len(mot)}c"
                        # Remplacer le mot incorrect par le mot correct
                        self.text_box.delete(start_idx, end_idx)
                        self.text_box.insert(start_idx, correct_mot)
                    else:
                        # Marquer le mot comme incorrect s'il n'y a pas une seule suggestion
                        start_idx = self.text_box.search(mot, "1.0", tk.END)
                        if not start_idx:
                            continue
                        end_idx = f"{start_idx} + {len(mot)}c"
                        # print(start_idx, end_idx)
                        self.text_box.tag_add("incorrect", start_idx, end_idx)
        self.add_to_ui_queue(verify)

    def show_context_menu(self, event) -> None:
        """
        Affiche un menu contextuel de suggestions orthographiques sur clic droit.

        Args:
            event: Événement de clic droit Tkinter.
        """
        def show_menu():
            # Obtenir la position du clic droit dans le widget Text
            index = self.text_box.index(f"@{event.x},{event.y}")

            # Obtenir la ligne complète où le clic droit a eu lieu
            line_start = f"{index.split('.')[0]}.0"
            line_end = f"{index.split('.')[0]}.end"
            line_text = self.text_box.get(line_start, line_end)

            # Obtenir la position relative du curseur dans la ligne
            cursor_pos_in_line = int(index.split('.')[1])

            # Utiliser une regex pour trouver le mot avec un trait d'union sous le curseur
            # Recherche de mots contenant des lettres, chiffres et traits d'union
            for match in re.finditer(r'\b[\w-]+\b', line_text):
                start, end = match.span()
                if start <= cursor_pos_in_line <= end:
                    incorrect_word = match.group(0)
                    word_start = f"{line_start} + {start}c"
                    word_end = f"{line_start} + {end}c"
                    break
            else:
                return  # Aucun mot trouvé sous le curseur

            # Vérifier si le mot est incorrect et obtenir des suggestions
            if not self.dico.check(incorrect_word):
                suggestions = self.dico.suggest(incorrect_word)

                personnalise_suggestions = [
                    s for s in suggestions if s in self.mots_personnels
                ]
                autres_suggestions = [
                    s for s in suggestions if s not in self.mots_personnels
                ]
                suggestions = personnalise_suggestions + autres_suggestions

                # Effacer le menu précédent et ajouter les nouvelles suggestions
                self.context_menu.delete(0, tk.END)
                for suggestion in suggestions:
                    self.context_menu.add_command(
                        label=suggestion,
                        command=lambda s=suggestion, ws=word_start, we=word_end: self.replace_word(s, ws, we)
                    )
                self.context_menu.add_separator()
                self.context_menu.add_command(
                    label="Ajouter au dictionnaire",
                    command=lambda: self.ajouter_mot_personnalise(incorrect_word)
                )
                self.context_menu.post(event.x_root, event.y_root)
        self.add_to_ui_queue(show_menu)

    def replace_word(self, suggestion: str, word_start: str, word_end: str) -> None:
        """
        Remplace un mot dans la textbox par une suggestion.

        Args:
            suggestion (str): Mot proposé.
            word_start (str): Position de début dans le widget Text.
            word_end (str): Position de fin.
        """
        def replace():
            self.save_text_box()
            # Remplacer le mot dans la text box
            self.text_box.delete(word_start, word_end)
            self.text_box.insert(word_start, suggestion)
            # Retirer le marquage incorrect
            self.text_box.tag_remove("incorrect", word_start, word_end)

        self.add_to_ui_queue(replace)

    def ajouter_mot_personnalise(self, mot: str) -> None:
        """
        Ajoute un mot au dictionnaire personnalisé et relance la vérification.

        Args:
            mot (str): Le mot à ajouter.
        """

        self.mots_personnels.add(mot)
        self.dico.add(mot)
        self.verification_dico()

    def is_ouverte(self) -> bool:
        """
        Indique si la fenêtre de gestion des insertions est ouverte.

        Returns:
            bool: True si ouverte, sinon False.
        """

        return self.fenetre_gestion_ouverte

    def clear_text_box(self):
        pass

    def set_service(self, service: str) -> None:
        """
        Modifie le service (et donc l'IP/Port du serveur) puis force la reconnexion.
        """
        # 1) Mémoriser le service sélectionné
        self.app.config.service = service

        # 2) Mettre à jour l’UI immédiatement
        self._update_title_window()
        self._update_barre_status()

        # 3) Tenter la reconnexion vers le nouveau serveur
        success = self.engine.restart_connection(
            ip=self.app.config.server_ip,
            port=int(self.app.config.port)
        )

        # 4) Afficher le résultat
        self.app.status_server = success
        self._update_barre_status()

    def toggle_play_audio(self) -> None:
        """
        Met à jour l'option `play_audio` depuis la case à cocher utilisateur.
        """

        self.app.config.play_audio = self.play_audio_var.get()

    def handle_dropped_file(self, file_path: str) -> None:
        """
        Gère un fichier glissé-déposé. (Ici, la fonctionnalité n’est pas encore implémentée.)

        Args:
            file_path (str): Chemin vers le fichier audio.
        """

        update_status_bar(self.status_bar, text=f'Traitement du fichier : {file_path}',
                          bg='lightblue', fg='darkblue', anchor=tk.W)
        self.unpause(file_path)

    def log(self, text: str = "", nb_mots: int = 0) -> None:
        """
        Envoie un log de type 'transcription' au serveur distant.

        Args:
            text (str): Texte de la transcription à inclure dans le log.
        """

        model = self.engine.get_model()

        if self.file_source is not None:
            mode = f"[{self.mode.name}] - fichier: {self.file_source}"
        else:
            mode = f"{self.mode.name}"
        envoyer_log(event="transcription",
                    texte=text,
                    nb_mots=nb_mots,
                    mode=mode,
                    model=model,)

    import threading

    def add_to_ui_queue(self, func, *args, **kwargs):
        """Ajoute une tâche à la file d'attente UI pour exécution dans le thread principal."""
        task_id = (func, args, tuple(kwargs.items()))  # Identifiant unique pour la tâche
        if task_id in self.pending_tasks:
            # print(f"Tâche déjà en attente : {func.__name__}")
            return  # Ignorez les doublons
        self.pending_tasks.add(task_id)

        def safe_task():
            try:
                # print(f"Exécution de la tâche réelle : {func.__name__}({args}, {kwargs})")
                func(*args, **kwargs)
            except Exception as e:
                print(f"Erreur dans la tâche ajoutée à UI_QUEUE : {e}")
            finally:
                self.pending_tasks.remove(task_id)  # Retirez la tâche après exécution

        # Vérifiez si vous êtes dans le thread principal Tkinter
        if threading.current_thread() == threading.main_thread():
            # print(f"Exécution immédiate de la tâche : {func.__name__}({args})")
            safe_task()  # Exécute immédiatement si dans le thread principal
        else:
            # print(f"Tâche ajoutée à UI_QUEUE : {func.__name__}({args})")
            UI_QUEUE.put(safe_task)
