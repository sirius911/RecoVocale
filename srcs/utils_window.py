import os
import sys
import tkinter as tk
from tkinter import BooleanVar
from PIL import Image, ImageTk
from info import DIRECT, RECORD
from ToolTip import ToolTip

def get_config_path(file:str):
    """Retourne le chemin du fichier de configuration du micro dans %APPDATA%"""
    config_dir = os.path.join(os.getenv('APPDATA'), 'RecoVocale')
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    return os.path.join(config_dir, file)

def resource_path(relative_path):
    """Obtenir le chemin absolu d'une ressource, en tenant compte du fait qu'on est dans un exécutable ou non"""
    try:
        # PyInstaller crée un dossier temporaire et stocke le chemin dans _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def _load_and_resize_image(path, size):
     image = Image.open(path)
     image = image.resize(size, Image.LANCZOS)  # Use LANCZOS for high-quality downsizing
     return ImageTk.PhotoImage(image)

def create_buttons(self):
     #--------------------------------BOUTON -------------------------------------

     # Load, resize and convert images using Pillow
     button_width = self.mode.button_width
     self.record_image = _load_and_resize_image(resource_path("Icons/pause.png"), (button_width, button_width))
     self.pause_image = _load_and_resize_image(resource_path("Icons/rec.png"), (button_width, button_width))
     
     self.button_frame = tk.Frame(self.root)
     self.button_frame.pack(pady=10)

     self.rec_button = tk.Button(self.button_frame, image=self.record_image, command=self.toggle_start_stop)
     self.rec_button.pack(side=tk.RIGHT, padx=5, pady=10)

     ToolTip(self.rec_button, f"({self.app.keyboard_shortcut})")

     self.rec_canvas = tk.Canvas(self.button_frame, width=button_width, height=button_width)
     self.rec_circle = self.rec_canvas.create_oval(2, 2, button_width, button_width, fill="grey")
     self.rec_canvas.pack(side=tk.LEFT, padx=5)

def create_menus(self):
    self.menu_bar = tk.Menu(self.root)
    self.root.config(menu=self.menu_bar)

    # Menu Paramètres
    self.settings_menu = tk.Menu(self.menu_bar, tearoff=0)
    self.menu_bar.add_cascade(label="Paramètres", menu=self.settings_menu)

    # Raccourci Clavier
    self.settings_menu.add_command(label="Raccourci Clavier", command=self.app.change_shortcut)
    
    # Mode
    self.mode_menu = tk.Menu(self.settings_menu, tearoff=0)
    # self.mod_var = tk.StringVar()
    self.settings_menu.add_cascade(label="Mode", menu=self.mode_menu)
    self.mode_menu.add_radiobutton(label='Direct',
                                   variable=self.mod_var,
                                   value=DIRECT,
                                   command= lambda: self.app.switch_mode(DIRECT))
    self.mode_menu.add_radiobutton(label='Enregistrement',
                                   variable=self.mod_var,
                                   value=RECORD,
                                   command= lambda: self.app.switch_mode(RECORD))

    # Autres options du menu Paramètres
    self.settings_menu.add_separator()
    self.settings_menu.add_command(label="Info", command=self.info)
    self.settings_menu.add_separator()
    self.settings_menu.add_command(label="Connecte", command=self.start_client)
    self.settings_menu.add_command(label="Deconnect", command=self.stop_client)
    self.debug_var = BooleanVar(value=self.app.config.debug)
    self.settings_menu.add_checkbutton(label="Debug", variable=self.debug_var, 
                                   command=lambda:setattr(self.app.config, 'debug', self.debug_var.get()))
    self.settings_menu.add_separator()
    self.settings_menu.add_command(label="Quitter", command=self.exit_app)

    # Nouveau menu Édition
    self.edit_menu = tk.Menu(self.menu_bar, tearoff=0)
    self.menu_bar.add_cascade(label="Édition", menu=self.edit_menu)

    # Options du menu Édition
    self.edit_menu.add_command(label="Copier", command=self.copy_to_clipboard)
    self.edit_menu.add_command(label="Coller", command=self.app.paste_from_clipboard)
