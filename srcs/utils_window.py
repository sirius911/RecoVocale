import os
import sys
import tkinter as tk
from PIL import Image, ImageTk

from info import DIRECT, REDUIT, APPRENTI
from ToolTip import ToolTip
from queue_manager import UI_QUEUE

bubble = None
label_in_bubble = None


def get_config_path(file: str) -> str:
    """
    Retourne le chemin absolu d’un fichier de configuration dans le répertoire `%APPDATA%/RecoVocale`.

    Args:
        file (str): Nom du fichier.

    Returns:
        str: Chemin complet vers le fichier dans le répertoire de config.
    """

    config_dir = os.path.join(os.getenv('APPDATA'), 'RecoVocale')
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    return os.path.join(config_dir, file)


def resource_path(relative_path: str) -> str:
    """
    Donne le chemin absolu vers une ressource, compatible avec PyInstaller.

    Args:
        relative_path (str): Chemin relatif dans le projet.

    Returns:
        str: Chemin absolu vers la ressource.
    """

    try:
        # PyInstaller crée un dossier temporaire et stocke le chemin dans _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def _load_and_resize_image(path: str, size: tuple[int, int]) -> ImageTk.PhotoImage:
    """
    Charge et redimensionne une image pour affichage dans Tkinter.

    Args:
        path (str): Chemin vers l’image.
        size (tuple): Dimensions (largeur, hauteur).

    Returns:
        ImageTk.PhotoImage: Image redimensionnée prête à être utilisée dans un widget Tkinter.
    """

    image = Image.open(path)
    image = image.resize(size, Image.LANCZOS)  # Use LANCZOS for high-quality downsizing
    return ImageTk.PhotoImage(image)


def create_buttons(self) -> None:
    """
    Crée et affiche dynamiquement les boutons de contrôle (rec, pause, trash...),
    selon le mode actif. Attache les raccourcis et icônes aux boutons.
    """

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
    self.rec_button = tk.Button(self.button_frame, image=self.record_image,
                                command=self.toggle_start_stop, state=tk.DISABLED)
    self.rec_button.grid(row=0, column=0, padx=padx)
    if self.app.status_server is True:
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
        self.learning_button = tk.Button(self.button_frame, image=self.learn_image,
                                         command=self.learning, state=tk.DISABLED)
        self.learning_button.grid(row=0, column=3, padx=padx)
        self.play_button = tk.Button(self.button_frame, image=self.play_image, command=self.play, state=tk.DISABLED)
        self.play_button.grid(row=0, column=4, padx=padx)
    # Center the buttons within the button_frame by configuring columns in button_frame
    self.button_frame.grid_columnconfigure(0, weight=1)
    self.button_frame.grid_columnconfigure(1, weight=1)
    self.button_frame.grid_columnconfigure(2, weight=1)


def change_toolTip(button: tk.Widget, texte: str) -> None:
    """
    Attribue une infobulle à un bouton.

    Args:
        button (tk.Widget): Le bouton auquel assigner une infobulle.
        texte (str): Texte de l’infobulle.
    """

    if button and button.winfo_exists():
        ToolTip(button, f"{texte}")


def update_status_bar(status_bar: tk.Widget, text: str, bg: str = None, fg: str = None, anchor: str = None) -> None:
    """
    Met à jour les propriétés d'une barre de statut (ou tout autre widget Tkinter).

    Args:
        status_bar (tk.Widget): Référence au widget Tkinter à mettre à jour.
        text (str): Texte à afficher dans la barre de statut.
        bg (str, optional): Couleur de fond. Par défaut, aucune modification.
        fg (str, optional): Couleur du texte. Par défaut, aucune modification.
        anchor (str, optional): Positionnement du texte (tk.W, tk.CENTER, tk.E, etc.). Par défaut, aucune modification.
    """

    def update():
        if text is not None:
            status_bar.config(text=text)
        if bg is not None:
            status_bar.config(bg=bg)
        if fg is not None:
            status_bar.config(fg=fg)
        if anchor is not None:
            status_bar.config(anchor=anchor)

    # Ajouter la mise à jour à la file d'attente pour exécution dans le thread principal
    UI_QUEUE.put(update)


def show_messagebox(message_type: str, title: str, message: str) -> None:
    """
    Affiche une boîte de dialogue Tkinter (messagebox) via UI_QUEUE.

    Args:
        message_type (str): Type de boîte de dialogue (warning, info, error, etc.).
        title (str): Titre de la boîte de dialogue.
        message (str): Message à afficher.
    """
    from tkinter import messagebox

    def show():
        if message_type == "warning":
            messagebox.showwarning(title, message)
        elif message_type == "info":
            messagebox.showinfo(title, message)
        elif message_type == "error":
            messagebox.showerror(title, message)
        else:
            raise ValueError(f"Type de message inconnu : {message_type}")

    # Ajouter la tâche à la file d'attente pour exécution dans le thread principal
    UI_QUEUE.put(show)
