# from utils_socket import check_server_status
import time
from info import *
from Transcription import Transcription
import tkinter as tk
from insertions import FenetreGestion

class Mode:
    def __init__(self, app):
        self.app = app
        self.root = app.root
        self.mod_var = tk.StringVar()
        self.transcription = Transcription()
        self.fenetre_gestion_ouverte = False  # Attribut pour savoir si la fenêtre est ouverte
        self.simulator_keyboard = None
        self.transcription_en_cours = False
        self.enter()

    def enter(self):
        self.root.resizable(self.mode.resizable, self.mode.resizable)
        self.root.attributes("-topmost", self.mode.topmost)
        self.root.geometry(f"{self.mode.window_width}x{self.mode.window_height}+{self.app.config.x_window}+{self.app.config.y_window}")
        if self.mode == REDUIT:
            self.root.title(f"RV v{VERSION}")
        else:
            self.root.title(f"RecoVocale [{self.app.config.server_ip}:{self.app.config.port}] (v{VERSION}) {"" if self.app.status_server else "not"} connected")

    def get_selected_text(self):
        return self.transcription.get()
    
    def valid_transcriptions(self):
        self.stop_client()
    
    def stop_client(self):
        self.transcription.validation()
        if self.client_manager:
            self.client_manager.stop_client()
        self.app.recording = False
        self.update()

    def copy_to_clipboard(self):
        self.status_bar.config(text='- Copie -', bg='lightblue', fg='darkblue', anchor=tk.CENTER)
        self.root.clipboard_clear()
        self.root.clipboard_append(self.transcription.get())
        time.sleep(0.5)
        self._update_barre_status()

    def pause(self):
        self.client_manager.pause()
        self.app.recording = False
        self.update()

    def unpause(self):
        if self.app.status_server == True:
            if not self.app.recording:
                if self.client_manager.client:
                    self.client_manager.client.set_pause(False)
                else:
                    self.client_manager.start_client(self.app.loop)
                self.app.recording = True
        self.update()

    def exit_app(self):
        # self.icon.stop()
        self.app.on_closing()

    def _update_rec_circle(self):
        fill = 'red' if self.app.recording else 'grey'
        self.rec_canvas.itemconfig(self.rec_circle, fill=fill)

    def _update_image_button(self):
        if self.app.recording:
            self.rec_button.config(image=self.pause_image)
        else:
            self.rec_button.config(image=self.record_image)

    def _update_barre_status(self):
        if self.mode == REDUIT:
            message = f"RecoVocale {VERSION}"
        else:
            message = f"RecoVocale [{self.app.config.server_ip}:{self.app.config.port}] (v{VERSION}) {"" if self.app.status_server else "not"} connected"

        if self.app.status_server == False:
            self.status_bar.config(text=message, fg='red', anchor=tk.W)
        elif self.app.recording:
            self.status_bar.config(text="RECORDING ...", fg='black', bg='red', anchor=tk.CENTER)
        elif self.transcription_en_cours:
            self.status_bar.config(text="Transcription ...en cours", bg='lightblue', fg='darkblue', anchor=tk.W)
        else:
            self.status_bar.config(text=message, bg='lightblue', fg='darkblue', anchor=tk.W)

    def update(self):
        self._update_rec_circle()
        self._update_image_button()
        self._update_barre_status()
        # self.app.info()

    def name(self):
        return self.mode.name
    
    def select_text_box(self, dir = "left"):
        pass

    def undo(self, event=None):
        pass
    
    def toggle_start_stop(self):
        """
        Toggle the start/stop state of the transcription client.
        """
        if self.app.recording:
            self.pause()
        else:
            self.unpause()

    def toggle_debug(self):
        #maj de la variable config
        self.app.config.debug = self.debug_var.get()
        if self.app.config.debug:
            self.app.console_debug.debug_window.deiconify()
        else:
            self.app.console_debug.debug_window.withdraw()

    def exit(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        # return self.transcription.get() # on retourne la transcription en cours

    def ouvrir_gestion_insertions(self):
        """Ouvre la fenêtre de gestion des insertions"""
        if not self.fenetre_gestion_ouverte:
            self.fenetre_gestion = FenetreGestion(self.root, self.app.insertions, self.fermer_gestion_insertions)
            self.fenetre_gestion.protocol("WM_DELETE_WINDOW", self.fermer_gestion_insertions)
            self.fenetre_gestion_ouverte = True

    def fermer_gestion_insertions(self):
        """Méthode appelée lorsque la fenêtre de gestion est fermée"""
        if self.fenetre_gestion:
            self.fenetre_gestion.destroy()
        self.fenetre_gestion_ouverte = False

    def is_ouverte(self):
        return self.fenetre_gestion_ouverte
    
    def clear_text_box(self):
        pass