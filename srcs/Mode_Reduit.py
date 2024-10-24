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
            mode=self.mode
        )
        super().enter()
        self.simulator_keyboard = Simulator(None, True)

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
        print("Pausing client in Mode Réduit")
        super().pause()

    def unpause(self):
        print("UnPausing client in Mode Réduit")
        super().unpause()

    def stop_client(self):
        print("Stop client in Mode Réduit")
        super().stop_client()

    def stop(self):
        self.stop_client()
        remove_bubble()

    def valid_transcriptions(self):
        self.stop_client()

    def update_transcriptions(self, message, ending):
        if message is not None:
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

    def clear_text_box(self):
        Simulator([Key.delete])

    def exit(self):
        remove_bubble()
        super().exit()
        return self.transcription.get() # on retourne la transcription en cours
