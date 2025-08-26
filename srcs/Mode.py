import threading
import enchant
import tkinter as tk
import pygame
from info import REDUIT, VERSION
from Insertions_editor import FenetreInsertions
from loger import envoyer_log
from queue_manager import UI_QUEUE
from utils_window import update_status_bar, show_messagebox
from mydict_editor import FenetreMyDict
from menus import toggle_menu_gestion_fenetre


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
        self.fenetre_gestion_ouverte = False  # Attribut pour savoir si la fenêtre est ouverte
        self.transcription_en_cours = False
        self.file_source = None  # peut etre un fichier audio
        # # Définir le chemin du répertoire de configuration dans %APPDATA%\RecoVocale
        self.dico = enchant.Dict("fr_FR")
        self.mots_personnels = set()
        self.model = ""
        # base_url = app.get_vt_server_url()
        self.vt = app.vt
        self.pile = ['']
        self.thread = None
        self.running_thread = False
        self.transcription_interrompue = False

        self.pending_tasks = set()  # a supprimer apres les debug

    def enter(self) -> None:
        """
        Applique les propriétés visuelles du mode à la fenêtre principale (taille, titre, topmost).
        """

        self.root.resizable(self.mode.resizable, self.mode.resizable)
        self.root.attributes("-topmost", self.mode.topmost)
        self.root.geometry(f"{self.mode.window_width}x{self.mode.window_height}+" +
                           f"{int(self.app.config.x_window)}+{int(self.app.config.y_window)}")
        self.root.update_idletasks()

        # Vérification de la position réelle
        rx, ry = self.root.winfo_rootx(), self.root.winfo_rooty()
        cx, cy = int(self.app.config.x_window), int(self.app.config.y_window)
        if (rx, ry) != (cx, cy):
            self.root.after(100, lambda: self.root.geometry(
                f"{self.mode.window_width}x{self.mode.window_height}+{cx}+{cy}"
            ))

        if self.mode == REDUIT:
            self.root.title(f"RV v{VERSION}")
        else:
            self.root.title(f"RecoVocale [{self.app.config.server_ip}:{self.app.config.port}] " +
                            f"(v{VERSION}) {'connected' if self.app.status_server else 'not connected'}")

        self.ui()

    def get_selected_text(self):
        return self.transcription.get()

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

    def unpause(self, audio_file: str | None = None):
        if self.app.recording or self.vt.is_recording or not self.app.status_server:
            return
        try:
            self.vt.start()
            self.app.recording = True
            self.on_record_start()
        except Exception as e:
            update_status_bar(self.status_bar, f"Erreur start micro: {e}",
                              bg="red", fg="lightblue", anchor=tk.W)

    def pause(self) -> None:
        if not self.app.recording and not self.vt.is_recording:
            return
        text = ""
        try:
            text = self.vt.stop()
        except Exception as e:
            update_status_bar(self.status_bar, f"Erreur stop/transcription: {e}",
                              bg="lightblue", fg="darkblue", anchor=tk.W)
        finally:
            self.app.recording = False
        if text and text.strip():
            self.handle_final_text(text)
        update_status_bar(self.status_bar, "Transcription terminée",
                          bg='lightblue', fg='darkblue', anchor=tk.W)

    # Hooks à surcharger
    def on_record_start(self):
        self.update()
        pass

    def handle_final_text(self, text: str):
        pass

    def exit_app(self) -> None:
        """Compat : ne fait que déléguer au nettoyage local, sans rappeler l'app."""
        return self.exit()

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

        # --- blocage si VoiceTranscriber serveur HS ---
        try:
            # self.app.status_server = self.vt.is_server_up()
            if not self.app.status_server:
                self.rec_button.config(state=tk.DISABLED)
                from utils_window import update_status_bar
                update_status_bar(self.status_bar,
                                  text="Serveur VT indisponible",
                                  bg="lightblue", fg="darkblue", anchor=tk.W)
                return
            else:
                self.rec_button.config(state=tk.NORMAL)
        except Exception:
            self.rec_button.config(state=tk.DISABLED)
            return

        if self.app.recording:
            self.rec_button.config(image=self.pause_image)
        else:
            self.rec_button.config(image=self.record_image)

    def _update_barre_status(self) -> None:
        """
        Met à jour le message affiché dans la barre de statut selon l'état de l'application.
        """
        if self.mode == REDUIT:
            message = f"RecoVocale {VERSION}:{'connected' if self.app.status_server else 'not connected'} "
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
                message = f"Transcription de [{self.file_source}] ... en cours"
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

    def toggle_mydict_corrector(self) -> None:
        """
        Active/désactive le correcteur personnalisé (my.dic).
        """
        # Par défaut True si l'attribut n'existe pas
        enabled = bool(self.mydict_var.get())
        self.app.config.dictionnaire = enabled

    def ouvrir_mydict_editor(self) -> None:
        """
        Ouvre la fenêtre d'édition du dictionnaire personnalisé (my.dic).
        """
        # S'assure que l'ouverture se fait dans le thread UI
        if not self.fenetre_gestion_ouverte:
            def _spawn():
                self.fenetre_mydict = FenetreMyDict(self.root, app=self.app, termine=self.fermer_mydict_editor)
                self.fenetre_gestion_ouverte = True

            self.add_to_ui_queue(_spawn)
            toggle_menu_gestion_fenetre(self, tk.DISABLED)

    def fermer_mydict_editor(self) -> None:
        """Callback appelé par FenetreMyDict à la fermeture."""
        try:
            # si la fenêtre existe encore (fermeture programmée), on la détruit proprement
            if getattr(self, "fenetre_mydict", None):
                try:
                    self.fenetre_mydict.destroy()
                except Exception:
                    pass
        finally:
            self.fenetre_mydict = None
            self.fenetre_gestion_ouverte = False
            toggle_menu_gestion_fenetre(self, tk.NORMAL)

    def lance_vlc(self):
        """Ouvre une boîte de dialogue pour choisir un média, puis lance VLC déjà
        configuré pour sortir sur le pipe et commence la lecture."""
        show_messagebox(message_type="warning",
                        title="Ne fonctionne pas",
                        message="Cette fonctionnalité ne fonctionne pas encore ! \n Patience !")

    def exit(self) -> None:
        # stop VT si besoin
        try:
            if getattr(self, "vt", None) and getattr(self.vt, "is_recording", False):
                self.vt.stop()
        except Exception:
            pass

        # stop audio si besoin
        try:
            if getattr(self, "audio_playing", False):
                pygame.mixer.music.stop()
                self.audio_playing = False
        except Exception:
            pass

        # supprimer fichiers temp si présents
        import os
        for attr in ("temp_txt_file", "temp_wav_file"):
            path = getattr(self, attr, None)
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass

        # détruire les widgets du mode
        for widget in self.root.winfo_children():
            widget.destroy()

    def ouvrir_gestion_insertions(self) -> None:
        """
        Ouvre la fenêtre de gestion des insertions si elle n’est pas déjà ouverte.
        """

        if not self.fenetre_gestion_ouverte:
            def _spawn():
                self.fenetre_gestion = FenetreInsertions(self.root, insertions_xml=self.app.config.insertions,
                                                         termine=self.fermer_gestion_insertions)
                self.fenetre_gestion_ouverte = True
            self.add_to_ui_queue(_spawn)
            toggle_menu_gestion_fenetre(self, tk.DISABLED)

    def fermer_gestion_insertions(self) -> None:
        """
        Callback appelé par fenetre_gestion.
        """
        try:
            if getattr(self, "fenetre_gestion", None):
                try:
                    self.fenetre_gestion.destroy()
                except Exception as e:
                    print(f"erreur {e}")
        finally:
            self.fenetre_gestion = None
            self.fenetre_gestion_ouverte = False
            toggle_menu_gestion_fenetre(self, tk.NORMAL)

    def save_text_box(self) -> None:
        pass

    def is_ouverte(self) -> bool:
        """
        Indique si la fenêtre de gestion des insertions est ouverte.

        Returns:
            bool: True si ouverte, sinon False.
        """

        return self.fenetre_gestion_ouverte

    def clear_text_box(self):
        pass

    def toggle_play_audio(self) -> None:
        """
        Met à jour l'option `play_audio` depuis la case à cocher utilisateur.
        """

        self.app.config.play_audio = self.play_audio_var.get()

    def handle_dropped_file(self, file_path: str) -> None:
        """
        Transcrit un fichier déposé via VoiceTranscriber.transcribe_file(), en thread.
        """
        import threading
        self.file_source = file_path
        self.transcription_en_cours = True

        update_status_bar(self.status_bar,
                          text=f"Transcription de [{file_path}] ... en cours",
                          bg="red", fg="black", anchor=tk.CENTER)

        def worker():
            try:
                texte = self.vt.transcribe_file(file_path, language="fr")
            except Exception as e:
                def _fail(e):
                    update_status_bar(self.status_bar,
                                      text=f"Erreur transcription fichier: {e}",
                                      bg="lightblue", fg="darkblue", anchor=tk.W)
                self.add_to_ui_queue(_fail, e)
                return
            finally:
                self.transcription_en_cours = False
                self.file_source = None

            if texte and texte.strip():
                # délègue au comportement du mode (Direct = insert ; Réduit = coller)
                self.add_to_ui_queue(self.handle_final_text, texte)

            def _done():
                update_status_bar(self.status_bar,
                                  text="Transcription terminée",
                                  bg="lightblue", fg="darkblue", anchor=tk.W)
            self.add_to_ui_queue(_done)

        threading.Thread(target=worker, daemon=True).start()

    def log(self, text: str = "", nb_mots: int = 0) -> None:
        """
        Envoie un log de type 'transcription' au serveur distant.

        Args:
            text (str): Texte de la transcription à inclure dans le log.
        """

        model = "Non connu"

        if self.file_source is not None:
            mode = f"[{self.mode.name}] - fichier: {self.file_source}"
        else:
            mode = f"{self.mode.name}"
        envoyer_log(event="transcription",
                    texte=text,
                    nb_mots=nb_mots,
                    mode=mode,
                    model=model,)

    def add_to_ui_queue(self, func, *args, **kwargs):
        """Ajoute une tâche à la file d'attente UI pour exécution dans le thread principal."""
        if getattr(self.app, "shutting_down", False):
            return  # on n'empile plus de tâches UI quand on ferme

        task_id = (func, args, tuple(kwargs.items()))  # Identifiant unique pour la tâche
        if task_id in self.pending_tasks:
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
