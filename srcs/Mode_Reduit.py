from Mode import Mode
import tkinter as tk
from utils_window import create_menus, create_buttons, show_bubble_message, remove_bubble
from info import REDUIT, VERSION
from ClientManager import ClientManager
from utils_keyboard import Simulator
from pynput.keyboard import Key

class Mode_Reduit(Mode):
    def enter(self):
        self.mode = REDUIT
        # self.app.simulate_keyboard = REDUIT.simule_keyboard
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
        )
        super().enter()
        self.simulator_keyboard = Simulator(None, True)

    def ui(self): 
        create_menus(self)
        create_buttons(self)

        # Configure the grid system of the root window
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # # Create the text box frame
        # self.text_box_frame = tk.Frame(self.root)
        # self.text_box_frame.grid(row=1, column=0, sticky="nsew")

        # # Add scrollbar to the text box
        # self.text_box_scrollbar = tk.Scrollbar(self.text_box_frame)
        # self.text_box_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # # Add the text box
        # self.text_box = tk.Text(self.text_box_frame, yscrollcommand=self.text_box_scrollbar.set)
        # self.text_box.pack(fill=tk.BOTH, expand=True)

        # # Configure the selection tag
        # self.text_box.tag_configure("sel", background="yellow", foreground="black")

        # # Attach the scrollbar to the text box
        # self.text_box_scrollbar.config(command=self.text_box.yview)

        # Create the status bar at the bottom of the window
        self.status_bar = tk.Label(self.root, text=f"RecoVocale {VERSION}", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=2, column=0, sticky="ew")

    def pause(self):
        if self.app.config.debug:
            print("Pausing client in Mode Réduit")
        super().pause()

    def unpause(self):
        if self.app.config.debug:
            print("UnPausing client in Mode Réduit")
        super().unpause()

    def stop_client(self):
        print("Stop client in Mode Réduit")
        super().stop_client()

    def stop(self):
        self.stop_client()

    def valid_transcriptions(self):
        self.stop_client()

    def update_transcriptions(self, message, ending):
        self.transcription.update(message, -1)
        if ending:
            remove_bubble()
            # copie dans clipboard
            self.root.clipboard_clear()
            self.root.clipboard_append(self.transcription.text_en_cours)
            # coller
            Simulator([Key.ctrl, 'v'])
            # Simulator(self.transcription.text_en_cours)
            self.transcription.validation()
            self.status_bar.config( text=f'RecoVocale {VERSION}', bg='lightblue', fg='darkblue', anchor=tk.W)
            # self.simulator_keyboard.init()
        else:
            show_bubble_message(self.root, message)
            self.status_bar.config(text='* Transcription *', bg='lightblue', fg='darkblue', anchor=tk.CENTER)


    def exit(self):
        super().exit()
        return self.transcription.get() # on retourne la transcription en cours
