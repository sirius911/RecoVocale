import os
import sys
import threading
import tkinter as tk
from screeninfo import get_monitors
from tkinter import BooleanVar
from PIL import Image, ImageTk

from info import DIRECT, REDUIT, APPRENTI, FICHIER
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


def create_menus(self) -> None:
    """
    Crée la barre de menus principale.

    - Paramètres (raccourcis, service, etc.)
    - Mode  (Direct, Réduit, Apprentissage, Transcription…)
    - Édition (copier, coller, undo…)
    """

    # Barre de menus principale
    self.menu_bar = tk.Menu(self.root)
    self.root.config(menu=self.menu_bar)

    # =========================
    # 1. Paramètres
    # =========================
    self.settings_menu = tk.Menu(self.menu_bar, tearoff=0)
    self.menu_bar.add_cascade(label="Paramètres", menu=self.settings_menu)

    # — Raccourci clavier
    self.settings_menu.add_command(label="Raccourci Clavier",
                                   command=self.app.change_shortcut)

    # — Service
    self.service_var = tk.StringVar(value=self.app.config.service)
    self.service_menu = tk.Menu(self.settings_menu, tearoff=0)
    self.settings_menu.add_cascade(label="Service", menu=self.service_menu)

    for service in self.app.config.get_services():
        self.service_menu.add_radiobutton(label=service,
                                          variable=self.service_var,
                                          value=service,
                                          command=lambda s=service: self.set_service(s))

    # — Divers
    self.settings_menu.add_separator()
    self.play_audio_var = BooleanVar(value=self.app.config.play_audio)
    self.settings_menu.add_checkbutton(label="Lecture audio locale",
                                       variable=self.play_audio_var,
                                       command=self.toggle_play_audio)

    self.settings_menu.add_separator()
    self.settings_menu.add_command(label="Gestion des Insertions",
                                   command=self.ouvrir_gestion_insertions)
    self.settings_menu.add_separator()

    self.debug_var = BooleanVar(value=self.app.config.debug)
    self.settings_menu.add_checkbutton(label="Debug", variable=self.debug_var,
                                       command=self.toggle_debug)
    self.dico_var = BooleanVar(value=self.app.config.dictionnaire)
    self.settings_menu.add_checkbutton(label="Dictionnaire", variable=self.dico_var,
                                       command=self.toggle_dictionnaire)

    self.settings_menu.add_separator()
    self.settings_menu.add_command(label="Quitter", command=self.exit_app)

    # =========================
    # 2. Édition
    # =========================
    self.edit_menu = tk.Menu(self.menu_bar, tearoff=False)
    self.menu_bar.add_cascade(label="Édition", menu=self.edit_menu)

    # — Undo
    self.undo_menu = self.edit_menu.add_command(label="Undo (Ctrl+Z)",
                                                command=self.undo)
    self.root.bind_all("<Control-z>", self.undo)
    self.edit_menu.entryconfig(0, state='disabled')

    # — Copier / Coller
    self.edit_menu.add_separator()
    self.edit_menu.add_command(label="Copier (Ctrl+C)",
                               command=self.copy_to_clipboard)
    self.edit_menu.add_command(label="Coller (Ctrl+V)",
                               command=self.app.paste_from_clipboard)

    # — Effacer (seulement en mode Direct)
    if self.mode == DIRECT:
        self.edit_menu.add_command(label="Effacer",
                                   command=self.clear_text_box)

    if self.mode == REDUIT:
        self.edit_menu.add_separator
        self.word_space_var = BooleanVar(value=self.app.config.word_space)
        self.edit_menu.add_checkbutton(label="Espace avant ", variable=self.word_space_var,
                                       command=self.toggle_word_space)

    # =========================
    # 3. Mode  (NOUVEAU menu racine)
    # =========================
    self.mod_var = tk.StringVar(value=self.mode)
    self.mode_menu = tk.Menu(self.menu_bar, tearoff=0)    # ← nouveau
    self.menu_bar.add_cascade(label="Mode", menu=self.mode_menu)  # ← nouveau

    self.mode_menu.add_radiobutton(label='Direct',
                                   variable=self.mod_var,
                                   value=DIRECT,
                                   command=lambda: self.app.switch_mode(DIRECT))
    self.mode_menu.add_radiobutton(label='Réduit',
                                   variable=self.mod_var,
                                   value=REDUIT,
                                   command=lambda: self.app.switch_mode(REDUIT))
    self.mode_menu.add_radiobutton(label='Apprentissage',
                                   variable=self.mod_var,
                                   value=APPRENTI,
                                   command=lambda: self.app.switch_mode(APPRENTI))
    self.mode_menu.add_radiobutton(label='Transcription Fichiers Audios',
                                   variable=self.mod_var,
                                   value=FICHIER,
                                   command=lambda: self.app.switch_mode(FICHIER))
    self.mode_menu.entryconfig(3, state='disabled')

    # =========================
    # 4. VLC
    # =========================
    # État « Utiliser VLC » – vrai ou faux
    self.vlc_var = tk.BooleanVar(value=getattr(self.app.config, "use_vlc", False))

    # Menu racine « VLC »
    self.vlc_menu = tk.Menu(self.menu_bar, tearoff=0)
    self.menu_bar.add_cascade(label="VLC", menu=self.vlc_menu)

    # Case à cocher « Utiliser VLC »
    self.vlc_menu.add_checkbutton(
        label="Utiliser VLC",
        variable=self.vlc_var,
        onvalue=True,
        offvalue=False,
        command=self.toggle_vlc      # ⇐ fonction décrite ci-dessous
    )

    # Lancer VLC
    self.vlc_menu.add_command(label="Charger un fichier avec VLC", command=self.lance_vlc)


def _show_bubble_message(parent: tk.Tk, message: str, background: str = "yellow") -> None:
    """
    Affiche ou met à jour une bulle flottante centrée sur l'écran contenant un message.

    Args:
        parent (tk.Tk): Fenêtre parente Tkinter.
        message (str): Texte à afficher.
        background (str): Couleur de fond de la bulle.
    """

    global bubble, label_in_bubble

    if bubble is not None and (
            not bubble.winfo_exists() or label_in_bubble is None or not label_in_bubble.winfo_exists()):
        bubble = None
        label_in_bubble = None
        return          # ← annule le callback résiduel

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
    if (bubble is None or not bubble.winfo_exists() or label_in_bubble is None or not label_in_bubble.winfo_exists()):
        # Widget invalide → on recrée proprement plus bas
        bubble = None
        label_in_bubble = None

    # Si la bulle existe déjà, mettre à jour le message et repositionner
    if bubble is not None:
        try:
            label_in_bubble.config(text=message)

            bubble_width = bubble.winfo_width()
            bubble_height = bubble.winfo_height()

            x = screen_x + (screen_width // 2) - (bubble_width // 2)
            y = screen_y + (screen_height // 2) - (bubble_height // 2)

            bubble.geometry(f"+{x}+{y}")
            bubble.update_idletasks()

        except tk.TclError:            # la fenêtre a été détruite juste après le test
            bubble = None
            label_in_bubble = None
            return

    else:
        # Créer la bulle
        try:
            bubble = tk.Toplevel(parent)
            bubble.wm_overrideredirect(True)
            bubble.attributes("-topmost", True)

            label_in_bubble = tk.Label(bubble, text=message, font=("Arial", 10),
                                       background=background, fg="black", borderwidth=0)
            label_in_bubble.pack(padx=10, pady=5)

            bubble_width = bubble.winfo_width()
            bubble_height = bubble.winfo_height()

            x = screen_x + (screen_width // 2) - (bubble_width // 2)
            y = screen_y + (screen_height // 2) - (bubble_height // 2)

            bubble.geometry(f"+{x}+{y}")
            bubble.update_idletasks()

        except tk.TclError as e:
            print(f"[ERROR] à la création du bubble: {e}")


def get_text_bubble() -> str:
    """
    Retourne le texte actuellement affiché dans la bulle de message.

    Returns:
        str: Texte de la bulle, ou une chaîne vide si aucune bulle n'est active.
    """

    global label_in_bubble
    try:
        if label_in_bubble is not None:
            return label_in_bubble.cget("text")
        return ""
    except tk.TclError:
        return ""


def _remove_bubble() -> str:
    """
    Ferme la bulle de message si elle existe.
    """

    global bubble, label_in_bubble
    text = ""
    try:
        if bubble is not None:
            text = get_text_bubble()
            bubble.destroy()
        # else:
        #     print("[utils_window] Aucune bulle à détruire.")
    except tk.TclError:
        # print(f"[utils_window] Erreur lors de la destruction de la bulle : {e}")
        pass
    finally:
        bubble = None
        label_in_bubble = None
        return text


def show_bubble_message(root: tk.Tk, message: str, background: str = "yellow") -> None:
    """
    Affiche ou met à jour une bulle flottante centrée sur l'écran contenant un message.

    Args:
        root (tk.Tk): Fenêtre parente Tkinter.
        message (str): Texte à afficher.
        background (str): Couleur de fond de la bulle.
    """

    def show():
        _show_bubble_message(root, message, background)

    # Ajouter la tâche à la file d'attente pour exécution dans le thread principal
    UI_QUEUE.put(show)


def remove_bubble(force: bool = False) -> str:
    """
    Ferme la bulle de message si elle existe.
    Si `force` est True, on exécute immédiatement (dans le thread courant)
    au lieu de passer par UI_QUEUE.
    """
    def remove():
        return _remove_bubble()

    if force or threading.current_thread() == threading.main_thread():
        # appel direct : on évite tout délai
        return _remove_bubble()
    else:
        UI_QUEUE.put(remove)
        return ""


def update_bubble_background(color: str) -> None:
    """
    Modifie la couleur de fond de la bulle de message active.

    Args:
        color (str): Nouvelle couleur de fond.
    """

    global label_in_bubble
    if label_in_bubble is not None:
        label_in_bubble.config(background=color)


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
