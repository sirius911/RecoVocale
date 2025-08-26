import tkinter as tk
from pygame import mixer
import tkinter.filedialog as filedialog
import tkinter.font as tkFont
from Mode_Direct import Mode_Direct
from menus import create_menus
from info import FICHIER


class Mode_Fichier(Mode_Direct):
    def __init__(self, app):
        super().__init__(app, FICHIER)
        self.enter()
        # self.transcription_interrompue = False
        self.transcription_fichier_en_cours = False
        self.audio_playing = False
        self.audio_duration = 0
        self.pos_lecture = 0
        self.temp_wav_file = None  # fichier à lire
        self.monitoring_events = False
        self.progress_tooltip = None
        self.en_pause = False

    def ui(self) -> None:
        create_menus(self)

        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # ------ Cadre supérieur avec les boutons -------
        self.frame_top = tk.Frame(self.root, pady=5)
        self.frame_top.grid(row=0, column=0, sticky="ew")

        # Bouton pour charger un fichier
        self.load_button = tk.Button(self.frame_top, text="📁 Choisir un fichier", command=self.charger_fichier)
        self.load_button.pack(side=tk.LEFT, padx=5)

        # Nom du fichier
        self.label_fichier = tk.Label(self.frame_top, text="Aucun fichier sélectionné")
        self.label_fichier.pack(side=tk.LEFT, padx=10)

        # Bouton lecture/pause
        self.play_pause_button = tk.Button(self.frame_top, text="▶️",
                                           command=lambda: self.toggle_play_pause(transcription=False))
        self.play_pause_button.pack(side=tk.LEFT, padx=5)

        # Bouton pour lancer la transcription
        self.transcribe_button = tk.Button(self.frame_top, text="📝 Transcrire",
                                           command=lambda: self.toggle_play_pause(transcription=True))
        self.transcribe_button.pack(side=tk.LEFT, padx=5)

        # Curseur de progression + timecode
        self.scale_var = tk.DoubleVar()
        self.progression = tk.Scale(self.frame_top,
                                    variable=self.scale_var,
                                    orient="horizontal",
                                    length=200,
                                    showvalue=0)
        self.progression.pack(side=tk.LEFT, padx=10)
        self.progression.bind("<ButtonRelease-1>", self.seek_audio)
        self.progression.bind("<B1-Motion>", self.update_timecode_preview)

        self.label_time = tk.Label(self.frame_top, text="00:00:00 / 00:00:00")
        self.label_time.pack(side=tk.LEFT)

        self.trash_button = tk.Button(self.frame_top,
                                      text="Effacer",
                                      command=self.clear_text_box)
        self.trash_button.pack(side=tk.LEFT, padx=5)

        # ------ Zone texte avec scroll ------
        self.text_box_frame = tk.Frame(self.root)
        self.text_box_frame.grid(row=1, column=0, sticky="nsew")

        self.text_box_scrollbar = tk.Scrollbar(self.text_box_frame)
        self.text_box_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.text_box = tk.Text(self.text_box_frame, yscrollcommand=self.text_box_scrollbar.set, wrap='word')
        self.text_box.pack(fill=tk.BOTH, expand=True)
        font = tkFont.Font(family="Calibri", size=12)
        self.text_box.configure(font=font)
        self.text_box.tag_config("incorrect", foreground="red", underline=True)
        self.text_box_scrollbar.config(command=self.text_box.yview)
        self.text_box.bind("<Key>", self.on_text_change)
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.text_box.bind("<Button-3>", self.show_context_menu)

        # Barre de statut
        self.status_bar = tk.Label(self.root, text="Mode Fichier - prêt", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=2, column=0, sticky="ew")

    def init_pygame_mixer(self):
        mixer.init()

    def charger_fichier(self):
        self.choisir_fichier()
        if self.file_source and self.file_source is not None:
            mixer.music.load(self.file_source)

    def choisir_fichier(self):
        filetypes = [("Fichiers audio ou vidéo", "*.wav *.mp3 *.mp4 *.flac *.ogg")]
        fichier = filedialog.askopenfilename(title="Choisir un fichier", filetypes=filetypes)
        if fichier:
            self.wait_label = tk.Label(self.root, text="⏳ Chargement...en cours", font=("Arial", 12), bg="yellow")
            self.wait_label.place(relx=0.5, rely=0.5, anchor="center")
            self.root.update()

            self.status_bar.config(text=f"Ouverture de {fichier.split('/')[-1]}",
                                   bg='lightblue',
                                   fg='darkblue',
                                   anchor=tk.W)
            self.file_source = fichier
            self.label_fichier.config(text=fichier.split("/")[-1])
            if not mixer.get_init():
                self.init_pygame_mixer()
            try:
                sound = mixer.Sound(fichier)
                self.audio_duration = sound.get_length()
                self.label_time.config(text=f"00:00:00 / {self.format_time(self.audio_duration)}")
                self.progression.config(to=int(self.audio_duration))
                self.pos_lecture = 0
            except Exception as e:
                print("Erreur durée audio:", e)
                self.label_time.config(text="00:00:00 / --:--:--")
            finally:
                self.status_bar.config(text=f"Fichier sélectionné : {fichier.split('/')[-1]}")
        if hasattr(self, "wait_label"):
            self.wait_label.destroy()

    def toggle_play_pause(self, transcription=False):
        """
        Lance ou met en pause la lecture du fichier audio, et met à jour le timecode.
        """

        if not self.file_source or self.file_source is None:
            print("pas de fichier")
            self.status_bar.config(text="Veuillez choisir un fichier.")
            return

        if not mixer.get_init():
            print("init de pygame")
            self.init_pygame_mixer()

        try:
            if not self.audio_playing:
                # Charger à chaque fois pour reprendre correctement
                # pygame.mixer.music.load(self.file_source)
                if self.en_pause:
                    mixer.music.unpause()
                    self.en_pause = False
                else:
                    mixer.music.play(start=self.pos_lecture)
                # mixer.music.play()
                self.audio_playing = True
                self.transcribe_button.config(text="📝 Pause")
                self.status_bar.config(text="Transcription en cours...")
                self.play_pause_button.config(text="⏸️")
                self.status_bar.config(text="Lecture en cours...")

                # Attendre un petit temps puis sauter à la bonne position
                # print(f"Je pose la lecture à {self.pos_lecture}")
                # self.root.after(200, lambda: pygame.mixer.music.set_pos(self.pos_lecture))
                if transcription:
                    self.unpause()
                    self.transcription_fichier_en_cours = True
                    self.transcription_interrompue = False
                self.update_timecode()
            else:
                # Pause
                mixer.music.pause()
                self.en_pause = True
                position_audio = mixer.music.get_pos()
                self.pos_lecture += position_audio/1000.0
                # pygame.mixer.music.pause()
                self.audio_playing = False
                self.transcribe_button.config(text="📝 Transcrire")
                self.status_bar.config(text=f"Transcription en pause [{self.format_time(self.pos_lecture)}]")
                self.play_pause_button.config(text="▶️")
                self.status_bar.config(text=f"Lecture en pause [{self.format_time(self.pos_lecture)}]")
                if self.transcription_fichier_en_cours:
                    self.transcription_fichier_en_cours = False
                    self.pause()
                    # self.stop_client()
        except Exception as e:
            print("Erreur lecture audio:", e)

    def format_time(self, seconds):
        seconds = int(seconds)
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02}:{m:02}:{s:02}"

    def update_timecode(self):
        """
        Met à jour le timecode et le curseur de progression pendant la lecture.
        """
        if self.audio_playing:

            current = (mixer.music.get_pos() / 1000.0)
            if not self.en_pause:
                current += self.pos_lecture
            total = self.audio_duration
            if current >= total:
                self.audio_playing = False
                self.en_pause = False
                self.play_pause_button.config(text="▶️")
                self.transcribe_button.config(text="📝 Transcrire")
                self.label_time.config(text=f"{self.format_time(total)} / {self.format_time(total)}")
                self.progression.set(total)
                return

            self.label_time.config(text=f"{self.format_time(current)} / {self.format_time(total)}")
            self.progression.set(current)
            self.root.after(200, self.update_timecode)

    def seek_audio(self, event):
        """
        Se déplace dans l'audio à la position donnée par le curseur.
        """
        if not self.file_source or self.audio_playing:
            return
        pos = self.scale_var.get()
        self.pos_lecture = pos
        print(f"position lecture apres seek_audio = {self.pos_lecture}")
        self.en_pause = False
        self.label_time.config(text=f"{self.format_time(pos)} / {self.format_time(self.audio_duration)}")

    def update_timecode_preview(self, event=None):
        """
        Met à jour le timecode pendant le déplacement du curseur, sans lancer la lecture.
        """
        pos = self.scale_var.get()
        total = self.audio_duration
        self.label_time.config(text=f"{self.format_time(pos)} / {self.format_time(total)}")
