import os
import tkinter as tk
from info import ModeStyle
from PIL import Image, ImageTk
from info import BUTTON_WIDTH_BIG, BUTTON_WIDTH_SMALL

def _load_and_resize_image(path, size):
     image = Image.open(path)
     image = image.resize(size, Image.LANCZOS)  # Use LANCZOS for high-quality downsizing
     return ImageTk.PhotoImage(image)

def create_buttons(self):
     #--------------------------------BOUTON -------------------------------------
     # Get the absolute path of the directory containing the script
     script_dir = os.path.dirname(os.path.abspath(__file__))

     # Load, resize and convert images using Pillow
     if self.mode == ModeStyle.BIG:
          button_width = BUTTON_WIDTH_BIG
     else:
          button_width = BUTTON_WIDTH_SMALL
     self.record_image = _load_and_resize_image(os.path.join(script_dir, "Icons/pause.png"), (button_width, button_width))
     self.pause_image = _load_and_resize_image(os.path.join(script_dir, "Icons/rec.png"), (button_width, button_width))

     self.button_frame = tk.Frame(self.root)
     self.button_frame.pack(pady=10)

     self.rec_button = tk.Button(self.button_frame, image=self.record_image, command=self._toggle_record)
     self.rec_button.pack(side=tk.RIGHT, padx=5, pady=10)

     self.rec_canvas = tk.Canvas(self.button_frame, width=button_width, height=button_width)
     self.rec_circle = self.rec_canvas.create_oval(2, 2, button_width, button_width, fill="grey")
     self.rec_canvas.pack(side=tk.LEFT, padx=5)

def create_menus(self):
     self.menu_bar = tk.Menu(self.root)
     self.root.config(menu=self.menu_bar)

     self.settings_menu = tk.Menu(self.menu_bar, tearoff=0)
     self.menu_bar.add_cascade(label="Paramètres", menu=self.settings_menu)

     self.micro_menu = tk.Menu(self.settings_menu, tearoff=0)
     self.settings_menu.add_cascade(label="Micro", menu=self.micro_menu)

     # self.update_micro_menu()

     # self.settings_menu.add_command(label="Raccourci Clavier", command=self.app.change_shortcut)
     self.mode_menu = tk.Menu(self.settings_menu, tearoff=0)
     self.settings_menu.add_cascade(label="Mode", menu=self.mode_menu)
     self.mode_menu.add_radiobutton(label='Grand fenêtre',
                                   command= lambda mode=ModeStyle.BIG: self.app.switch_mode(mode))
     self.mode_menu.add_radiobutton(label='Petite Fenêtre',
                                   command= lambda mode=ModeStyle.SMALL: self.app.switch_mode(mode))

     self.settings_menu.add_separator()
     self.settings_menu.add_command(label="Info", command=self.info)
     self.settings_menu.add_separator()

     self.settings_menu.add_command(label="Quitter", command=self.exit_app)