from utils_socket import check_server_status
from info import *
from Transcription import Transcription
import tkinter as tk

class Mode:
    def __init__(self, app):
        self.app = app
        self.root = app.root
        self.mod_var = tk.StringVar()
        self.transcription = Transcription()
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
    
    # def start_client(self):
    #     pass
    
    def stop_client(self):
        pass

    def copy_to_clipboard(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.transcription.get())

    # def hide_window(self):
    #     self.simulate_keyboard_var.set(True)
    #     self.is_hidden = True
    
    def exit_app(self):
        # self.icon.stop()
        self.app.on_closing()

    def _update_rec_circle(self):
        fill = 'red' if self.app.recording else 'grey'
        self.rec_canvas.itemconfig(self.rec_circle, fill=fill)

    def _update_image_button(self):
        if self.app.recording:
            self.rec_button.config(image=self.record_image)
        else:
            self.rec_button.config(image=self.pause_image)

    def _update_barre_status(self):
        if self.app.recording:
            message = "RECORDING ..."
        else:
            message = f"RecoVocale [{self.app.config.server_ip}:{self.app.config.port}] (v{VERSION}) {"" if self.app.status_server else "not"} connected"

        if self.app.status_server == False:
            self.status_bar.config(text=message, fg='red', anchor=tk.W)
        elif self.app.recording:
            self.status_bar.config(text=message, fg='black', bg='red', anchor=tk.CENTER)
        else:
            self.status_bar.config(text=message, bg='lightblue', fg='darkblue', anchor=tk.W)

    def update(self):
        self._update_rec_circle()
        self._update_image_button()
        self._update_barre_status()

    def info(self):
        #print info TODO: A mettre en fênetre
        print('--------------------------------------------------------------------')
        print(f"Version : v{VERSION}")
        if check_server_status(self.app.config.server_ip, self.app.config.port):
            _serv = f"Connected @{self.app.config.server_ip}:{self.app.config.port}"
        else:
            _serv = f"Not Connected @{self.app.config.server_ip}:{self.app.config.port}"
        print(f"Model = {self.client_manager.client.get_model_path()}")
        print(f"Serveur : {_serv}")
        print(f"Micro : {self.app.mic.micro_name if self.app.mic else None}")
        print(f"Mode = {self.name()} - Simulation Clavier: {self.app.simulate_keyboard}")
        print(f"Raccourci : {self.app.keyboard_shortcut}")
        print(f"Debug : {self.app.config.debug}")
        print(f"Position actuelle de la fenêtre : x={self.app.root.winfo_x()}, y={self.app.root.winfo_y()}")
        print('--------------------------------------------------------------------')

    def name(self):
        return self.mode.name
    
    def select_text_box(self, dir = "left"):
        pass
    
    def toggle_start_stop(self):
        """
        Toggle the start/stop state of the transcription client.
        """
        # print(f"mode = {self.name()}")
        if self.app.recording:
            self.pause()
        else:
            self.unpause()

    def exit(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        # return self.transcription.get() # on retourne la transcription en cours