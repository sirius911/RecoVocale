import os
import sys
import tkinter as tk
from tkinter import BooleanVar
from PIL import Image, ImageTk
from info import DIRECT, RECORD, REDUIT, APPRENTI
from ToolTip import ToolTip
from screeninfo import get_monitors

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
    padx = 2 if self.mode == REDUIT else 5
    pady = 10 if self.mode == REDUIT else 10
    # Load, resize and convert images using Pillow
    button_width = self.mode.button_width
    self.record_image = _load_and_resize_image(resource_path("Icons/rec.png"), (button_width, button_width))
    self.pause_image = _load_and_resize_image(resource_path("Icons/pause.png"), (button_width, button_width))
    self.trash_image = _load_and_resize_image(resource_path("Icons/trash.png"), (button_width, button_width))
    self.learn_image = _load_and_resize_image(resource_path("Icons/learn.jpg"), (button_width, button_width))
    self.play_image = _load_and_resize_image(resource_path("Icons/play.png"), (button_width, button_width))

    # Create a frame to hold the buttons and place it in the center
    self.button_frame = tk.Frame(self.root)
    self.button_frame.grid(row=0, column=0, pady=pady)

    # Configure grid layout for centering the buttons
    self.root.grid_columnconfigure(0, weight=1)  # Center the frame in the window

    # Add buttons and center them within the frame
    self.rec_button = tk.Button(self.button_frame, image=self.record_image, command=self.toggle_start_stop, state=tk.DISABLED)
    self.rec_button.grid(row=0, column=0, padx=padx)
    if self.app.status_server == True:
        self.rec_button.config(state=tk.NORMAL)
    change_toolTip(self.rec_button, self.app.config.shortcut)
    self.rec_canvas = tk.Canvas(self.button_frame, width=button_width, height=button_width)
    self.rec_circle = self.rec_canvas.create_oval(2, 2, button_width, button_width, fill="grey")
    self.rec_canvas.grid(row=0, column=1, padx=padx)

    if self.mode == DIRECT or self.mode == APPRENTI:
        self.trash_button = tk.Button(self.button_frame, image=self.trash_image, command=self.clear_text_box)
        self.trash_button.grid(row=0, column=2, padx=padx)
        self.trash_button.config(state=tk.DISABLED)
    if self.mode == APPRENTI:
        self.learning_button = tk.Button(self.button_frame, image=self.learn_image, command=self.learning, state=tk.DISABLED)
        self.learning_button.grid(row=0, column=3, padx=padx)
        self.play_button = tk.Button(self.button_frame, image=self.play_image, command=self.play, state=tk.DISABLED)
        self.play_button.grid(row=0, column=4, padx=padx)
    # Center the buttons within the button_frame by configuring columns in button_frame
    self.button_frame.grid_columnconfigure(0, weight=1)
    self.button_frame.grid_columnconfigure(1, weight=1)
    self.button_frame.grid_columnconfigure(2, weight=1)

    # Optional: If you want the frame to be centered horizontally in the window
    # self.button_frame.grid(row=0, column=0, sticky="n")  # This will keep it centered

def change_toolTip(button, texte):
    ToolTip(button, f"{texte}")

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

    self.settings_menu.add_cascade(label="Mode", menu=self.mode_menu)
    self.mode_menu.add_radiobutton(label='Direct',
                                   variable=self.mod_var,
                                   value=DIRECT,
                                   command= lambda: self.app.switch_mode(DIRECT))
    
    self.mode_menu.add_radiobutton(label='Réduit',
                                   variable=self.mod_var,
                                   value=REDUIT,
                                   command= lambda: self.app.switch_mode(REDUIT))

    self.mode_menu.add_radiobutton(label='Enregistrement',
                                   variable=self.mod_var,
                                   value=RECORD,
                                   command= lambda: self.app.switch_mode(RECORD))
    self.mode_menu.entryconfig('Enregistrement', state=tk.DISABLED) 

    self.mode_menu.add_radiobutton(label='Apprentissage',
                                   variable=self.mod_var,
                                   value=APPRENTI,
                                   command= lambda: self.app.switch_mode(APPRENTI))

    # Autres options du menu Paramètres
    self.settings_menu.add_separator()
    self.settings_menu.add_command(label="Gestion des Insertions", command=self.ouvrir_gestion_insertions)
    self.settings_menu.add_separator()

    self.debug_var = BooleanVar(value=self.app.config.debug)
    self.settings_menu.add_checkbutton(label="Debug", variable=self.debug_var, 
                                   command=self.toggle_debug)
    self.dico_var = BooleanVar(value=self.app.config.dictionnaire)
    self.settings_menu.add_checkbutton(label="Dictionnaire", variable=self.dico_var,
                                   command=self.toggle_dictionnaire)

    self.settings_menu.add_separator()
    self.settings_menu.add_command(label="Quitter", command=self.exit_app)

    # Nouveau menu Édition
    self.edit_menu = tk.Menu(self.menu_bar, tearoff=False)
    self.menu_bar.add_cascade(label="Édition", menu=self.edit_menu)

    # Options du menu Édition
    self.undo_menu = self.edit_menu.add_command(label="Undo (Ctrl+Z)", command=self.undo)
    self.root.bind_all("<Control-z>", self.undo)
    self.edit_menu.entryconfig(0, state='disabled')
    self.edit_menu.add_separator()
    self.edit_menu.add_command(label="Copier (Ctrl+C)", command=self.copy_to_clipboard)
    self.edit_menu.add_command(label="Coller (Ctrl+V)", command=self.app.paste_from_clipboard)
    if self.mode == DIRECT:
        self.edit_menu.add_command(label="Effacer", command=self.clear_text_box)

bubble = None
label_in_bubble = None

def show_bubble_message(parent, message):
    """Affiche ou met à jour la bulle de message avec une taille dynamique, sur le même écran que la fenêtre principale."""
    global bubble, label_in_bubble

    # Obtenir les informations des écrans
    monitors = get_monitors()

    # Récupérer les coordonnées de la fenêtre principale
    parent_x = parent.winfo_rootx()
    parent_y = parent.winfo_rooty()

    # Identifier l'écran où se trouve la fenêtre principale
    for monitor in monitors:
        if (monitor.x <= parent_x < monitor.x + monitor.width and
                monitor.y <= parent_y < monitor.y + monitor.height):
            target_monitor = monitor
            break
    else:
        # Si aucun écran correspondant n'est trouvé, utiliser le premier écran
        target_monitor = monitors[0]

    screen_x = target_monitor.x
    screen_y = target_monitor.y
    screen_width = target_monitor.width
    screen_height = target_monitor.height

    # Si la bulle existe déjà, mettre à jour le message et repositionner
    if bubble is not None:
        label_in_bubble.config(text=message)
        bubble.update_idletasks()

        bubble_width = bubble.winfo_width()
        bubble_height = bubble.winfo_height()

        x = screen_x + (screen_width // 2) - (bubble_width // 2)
        y = screen_y + (screen_height // 2) - (bubble_height // 2)

        bubble.geometry(f"+{x}+{y}")

    else:
        # Créer la bulle
        bubble = tk.Toplevel(parent)
        bubble.wm_overrideredirect(True)
        bubble.attributes("-topmost", True)

        label_in_bubble = tk.Label(bubble, text=message, font=("Arial", 10), background="yellow", fg="black", borderwidth=0)
        label_in_bubble.pack(padx=10, pady=5)

        bubble.update_idletasks()

        bubble_width = bubble.winfo_width()
        bubble_height = bubble.winfo_height()

        x = screen_x + (screen_width // 2) - (bubble_width // 2)
        y = screen_y + (screen_height // 2) - (bubble_height // 2)

        bubble.geometry(f"+{x}+{y}")

def remove_bubble():
    """Ferme la bulle de message si elle est active."""
    global bubble
    if bubble:
        bubble.destroy()
        bubble = None