from Mode import Mode
import tkinter as tk
from utils_window import create_menus, create_buttons
from info import REDUIT, VERSION
from ClientManager import ClientManager
from utils_keyboard import Simulator

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
            self.update_transcriptions  # Pass the callback to ClientManager
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
        self.transcription.update(message)
        if ending:
            self.transcription.validation()
            Simulator(self.transcription.text_transcription)
            self.simulator_keyboard.init()
        else:

            print("en calcul")
        # self.text_box.delete('1.0', tk.END)
        # self.text_box.insert(tk.END, self.transcription.get())
        # self.text_box.insert(tk.END, self.transcription.en_cours)
        # self.text_box.mark_set(tk.INSERT, tk.END)
        # self.text_box.see(tk.END)
