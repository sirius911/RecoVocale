from Mode import Mode
import tkinter as tk
from utils_window import create_menus, create_buttons
from info import DIRECT
from ClientManager import ClientManager

def trouver_bornes_mot_tk(phrase, curseur, direction='left'):
    # Si le curseur est à la fin, on le place au dernier caractère
    if curseur == -1:
        curseur = len(phrase) - 1

    # Assurer que le curseur est dans les bornes de la phrase
    curseur = max(0, min(len(phrase) - 1, curseur))
    
    if direction == 'left':
        # Trouver le début du mot à left
        debut = curseur
        while debut > 0 and phrase[debut].isspace():
            debut -= 1
        while debut > 0 and not phrase[debut - 1].isspace():
            debut -= 1
        
        # Trouver la fin du mot
        fin = curseur
        while fin < len(phrase) and not phrase[fin].isspace():
            fin += 1
        return debut, fin - 1
    
    elif direction == 'right':
        # Trouver le début du mot à right
        debut = curseur
        while debut < len(phrase) and phrase[debut].isspace():
            debut += 1
        
        fin = debut
        while fin < len(phrase) and not phrase[fin].isspace():
            fin += 1
        
        return debut, fin - 1
    
    else:
        raise ValueError("La direction doit être 'left' ou 'right'.")


class Mode_Direct(Mode):
    def enter(self):
        self.mode = DIRECT
        # self.app.simulate_keyboard = DIRECT.simule_keyboard
        self.mod_var.set(DIRECT)
        self.ui()
        #----------------- Lien Client Whisper -----------------------
        self.client_manager = ClientManager(
            self.app.config.server_ip,
            self.app.config.port,
            "fr",
            "small",
            False,
            True,
            False,
            "",
            self.update_transcriptions  # Pass the callback to ClientManager
        )
        super().enter()

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
        self.text_box = tk.Text(self.text_box_frame, yscrollcommand=self.text_box_scrollbar.set)
        self.text_box.pack(fill=tk.BOTH, expand=True)

        # Configure the selection tag
        self.text_box.tag_configure("sel", background="yellow", foreground="black")

        # Attach the scrollbar to the text box
        self.text_box_scrollbar.config(command=self.text_box.yview)

        # Create the status bar at the bottom of the window
        self.status_bar = tk.Label(self.root, text="Bienvenue dans l'application", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=2, column=0, sticky="ew")



        # self.copy_button = tk.Button(self.root, text="Copy", command=self.copy_to_clipboard)
        # self.copy_button.pack(pady=10)

        # self.clear_text_box_button = tk.Button(self.root, text="Clear", command=self.clear_text_box)
        # self.clear_text_box_button.pack(pady=10)

        # self.monitor_label = tk.Label(self.root, text="Monitoring du micro")
        # self.monitor_label.pack()

        # self.monitor_frame = tk.Frame(self.root)
        # self.monitor_frame.pack(pady=10)

        # self.rec_canvas = tk.Canvas(self.monitor_frame, width=20, height=20)
        # self.rec_circle = self.rec_canvas.create_oval(2, 2, 18, 18, fill="grey")
        # self.rec_canvas.pack(side=tk.LEFT, padx=5)

        # self.monitor_gauge = tk.Canvas(self.monitor_frame, width=300, height=20, bg="white")
        # self.monitor_gauge.pack(side=tk.LEFT, padx=5)

        # self.status_frame = tk.Frame(self.root)
        # self.status_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)

        # self.status_label = tk.Label(self.status_frame, text="Checking server status...")
        # self.status_label.pack(side=tk.LEFT, padx=(0, 5))

        # self.status_error = tk.Label(self.status_frame, text="", fg="red")
        # self.status_error.pack(side=tk.RIGHT, padx=(5, 0))

    # def start(self):
    #     self.start_client()

    # def start_client(self):
    #     pass
        # if self.config.debug:
        #     print("Starting client in App")
        # self.client_manager.start_client(self.app.loop)
        # self.pause()  # In pause 

    def pause(self):
        # if self.config.debug:
        print("Pausing client in App")
        self.client_manager.pause()
        self.app.recording = False
        self.update()

    def unpause(self):
        # if self.config.debug:
        print(f"Unpausing client in App")
        if self.app.status_server == True:
            if not self.app.recording:
                if self.client_manager.client:
                    self.client_manager.client.set_pause(False)
                else:
                    self.client_manager.start_client(self.app.loop)
                self.app.recording = True
        self.update()

    def stop_client(self):
        self.transcription.validation()
        # if self.config.debug:
        #     print("Stopping client in App")
        if self.client_manager:
            self.client_manager.stop_client()
        self.app.recording = False
        self.update()

    def stop(self):
        self.stop_client()

    def update_simulate_keyboard(self):
        self.app.simulate_keyboard = self.simulate_keyboard_var.get()
        if self.app.simulate_keyboard:
            self.app.simulator_keyboard.init()

    def valid_transcriptions(self):
        self.stop_client()
        # self.start_client()

    def get_selected_text(self):
        try:
            # Vérifie s'il y a une sélection
            if self.text_box.tag_ranges("sel"):
                # Récupère le texte sélectionné
                selected_text = self.text_box.get(tk.SEL_FIRST, tk.SEL_LAST)
                return selected_text
            else:
                # si aucune selection on envoi la transcription complète
                return self.transcription.get()
        except tk.TclError:
            # Gestion d'erreur si aucune sélection n'est faite
            return self.transcription.get()


    # def update_micro_menu(self):
    #     self.micro_menu.delete(0, tk.END)
    #     self.micro_list = []
    #     for i in range(self.app.audio.get_device_count()):
    #         dev = self.app.audio.get_device_info_by_index(i)
    #         if dev['maxInputChannels'] > 0:
    #             channels = dev['maxInputChannels']
    #             self.micro_list.append((dev['index'], dev['name'], channels))

    #     for idx, name, channels in self.micro_list:
    #         self.micro_menu.add_radiobutton(label=f"{name} (ID: {idx}, Channels: {channels})",
    #                                         command=lambda idx=idx: self.select_micro(idx))
    
    #     # Check the default microphone
    #     if self.app.selected_micro is not None:
    #         self.micro_menu.invoke(self.app.selected_micro)

    # def select_micro(self, idx):
    #     self.selected_micro = idx
    #     # self.app.update_mic_stream()

    def clear_text_box(self):
        """
        Clear the content of the text box.
        """
        self.valid_transcriptions()
        self.transcription.clear()

        self.text_box.delete('1.0', tk.END)
        self.root.update()

    # def update_monitoring(self):
    #     try:
    #         data = self.app.stream.read(1024, exception_on_overflow=False)
    #         audio_level = np.frombuffer(data, dtype=np.int16)
    #         audio_level = np.abs(audio_level).mean()
    #         self.monitor_gauge.delete("all")
    #         self.monitor_gauge.create_rectangle(0, 0, min(audio_level * 300 /2500, 300), 20, fill="green")
    #         self.update_icon_image(self.create_image(audio_level))
            
    #     except OSError as e:
    #         self.status_error.config(text="Erreur de lecture", fg="red")
    #         self.monitor_gauge.delete("all")
    #         self.monitor_gauge.create_rectangle(0, 0, 300, 20, fill="red")
    #         self.update_icon_image(self.create_error_image())

    # def update_status(self):
    #     super().update_status()
    #     text = 'Server status: Connected' if self.app.status_server else 'Server status: Not connected'
    #     self.status_label.config(text=text)


    def update_transcriptions(self, message, ending):
        # print(f"dans update_transcription ending = {ending}")
        self.transcription.update(message)
        if ending:
            self.transcription.validation()
        # if self.app.config.debug:
        #     print(f"transcription.encours = ({self.app.transcription.en_cours})")
        #     print(f"transcription.entier = '{self.app.transcription.entier}'")
        self.text_box.delete('1.0', tk.END)
        self.text_box.insert(tk.END, self.transcription.get())
        self.text_box.insert(tk.END, self.transcription.en_cours)
        self.text_box.mark_set(tk.INSERT, tk.END)
        self.text_box.see(tk.END)


    def select_text_box(self, dir = "left"):
        self.text_box.focus_set()
        # Effacer la sélection actuelle (retirer la surbrillance)
        self.text_box.tag_remove("sel", "1.0", tk.END)


        # Récupérer la position du curseur dans la text_box
        cursor_index = self.text_box.index(tk.INSERT)
       

        # Convertir cet index en offset numérique (compter les caractères depuis le début)
        line, column = map(int, cursor_index.split('.'))
        # print(f"cursor_index = ({line},{column})")
        if dir == "left":
            column -= 1
        else:
            column += 1
        # print(f"next cursor index = ({line},{column})")    
        current_position = int(self.text_box.index(f"{line}.0+{column}c").split('.')[1])

        # Récupérer tout le texte du text_box
        full_text =self.text_box.get("1.0", tk.END)
        
        # Trouver les bornes du mot à left ou à right
        start_pos, end_pos = trouver_bornes_mot_tk(full_text, current_position, dir)
        
        # Convertir ces bornes en indices Tkinter
        start_index = f"{line}.0+{start_pos}c"
        end_index = f"{line}.0+{end_pos + 1}c"  # Incrémenter pour inclure la dernière lettre
        # print(f"start_index = {start_index}, end_index = {end_index}")
        # Sélectionner le mot dans la text_box
        self.text_box.tag_add("sel", start_index, end_index)

        # Mettre le curseur à la fin ou au début  de la sélection
        if dir == "left":
            self.text_box.mark_set(tk.INSERT, start_index)
        else:
            self.text_box.mark_set(tk.INSERT, end_index)
        self.text_box.see(tk.INSERT)  # Faire défiler jusqu'au curseur