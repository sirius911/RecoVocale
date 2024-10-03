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
            self.app.config.server_ip,
            self.app.config.port,
            "fr",
            "small",
            False,
            True,
            False,
            "",
            self.update_transcriptions,  # Pass the callback to ClientManager
            self.app.insertions,
            self.is_ouverte,
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
        if self.app.config.debug:
            print("Stop client in Mode Réduit")
        super().stop_client()

    def stop(self):
        self.stop_client()

    # def update_simulate_keyboard(self):
    #     self.app.simulate_keyboard = self.simulate_keyboard_var.get()
    #     if self.app.simulate_keyboard:
    #         self.app.simulator_keyboard.init()

    def valid_transcriptions(self):
        self.stop_client()

    # def get_selected_text(self):
    #     try:
    #         # Vérifie s'il y a une sélection
    #         if self.text_box.tag_ranges("sel"):
    #             # Récupère le texte sélectionné
    #             selected_text = self.text_box.get(tk.SEL_FIRST, tk.SEL_LAST)
    #             return selected_text
    #         else:
    #             # si aucune selection on envoi la transcription complète
    #             return self.transcription.get()
    #     except tk.TclError:
    #         # Gestion d'erreur si aucune sélection n'est faite
    #         return self.transcription.get()

    # def clear_text_box(self):
    #     """
    #     Clear the content of the text box.
    #     """
    #     self.valid_transcriptions()
    #     self.transcription.clear()

    #     self.text_box.delete('1.0', tk.END)
    #     self.root.update()

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
