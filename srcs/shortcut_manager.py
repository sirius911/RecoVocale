import keyboard
import tkinter as tk
from tkinter import messagebox

from utils_window import change_toolTip


class ShortcutManager:
    """
    Gère les raccourcis clavier de l'application RecoVocale.

    Permet à l'utilisateur de modifier dynamiquement les raccourcis pour démarrer,
    arrêter la transcription et les appliquer dans l'interface graphique.
    """

    def __init__(self, root, current_mode, keyboard_shortcut, stop_keyboard_shortcut=""):
        """
        Initialise le gestionnaire de raccourcis.

        Args:
            root: Fenêtre principale Tkinter.
            current_mode: Référence au mode actif (Direct, Réduit, etc.).
            keyboard_shortcut (str): Raccourci clavier principal pour start/stop.
            stop_keyboard_shortcut (str): Raccourci clavier pour arrêter la transcription.
        """
        self.root = root
        self.current_mode = current_mode
        self.keyboard_shortcut = keyboard_shortcut
        self.stop_keyboard_shortcut = stop_keyboard_shortcut
        self.shortcut_window = None
        self.shortcut_entry = None
        self.stop_shortcut_entry = None
        self._pressed_keys = []

    def change_shortcut(self) -> None:
        """
        Ouvre une fenêtre de configuration pour modifier les raccourcis clavier.
        """

        self._initial_shortcut = self.keyboard_shortcut
        self._initial_stop_shortcut = self.stop_keyboard_shortcut
        self._shortcuts_saved = False

        self.root.attributes("-topmost", False)
        self.shortcut_window = tk.Toplevel(self.root)
        self.shortcut_window.title("Changer les raccourcis clavier")
        self.shortcut_window.attributes("-topmost", True)

        # Supprimer les raccourcis existants pendant l'édition
        keyboard.clear_all_hotkeys()

        # Label et champ pour Start/Stop
        tk.Label(self.shortcut_window, text="Raccourci démarrer / arrêter :").pack(pady=(10, 0))
        self.shortcut_entry = tk.Entry(self.shortcut_window)
        self.shortcut_entry.pack(pady=(0, 10))
        self.shortcut_entry.bind('<KeyPress>', self.on_key_press_start)
        self.shortcut_entry.bind('<KeyRelease>', self.on_key_release_start)

        # Label et champ pour Arrêter transcription
        tk.Label(self.shortcut_window, text="Raccourci arrêter transcription :").pack(pady=(10, 0))
        self.stop_shortcut_entry = tk.Entry(self.shortcut_window)
        self.stop_shortcut_entry.pack(pady=(0, 10))
        self.stop_shortcut_entry.bind('<KeyPress>', self.on_key_press_stop)
        self.stop_shortcut_entry.bind('<KeyRelease>', self.on_key_release_stop)

        # Bouton Enregistrer
        save_button = tk.Button(self.shortcut_window, text="Enregistrer", command=self.save_shortcuts)
        save_button.pack(pady=10)

        # Initialiser avec les raccourcis existants (ou vides)
        self.shortcut_entry.insert(0, self.keyboard_shortcut or "")
        self.stop_keyboard_shortcut = getattr(self, 'stop_keyboard_shortcut', '')
        self.stop_shortcut_entry.insert(0, self.stop_keyboard_shortcut or "")

        self.shortcut_window.protocol("WM_DELETE_WINDOW", self.on_close_shortcut_window)

    def on_close_shortcut_window(self) -> None:
        """
        Ferme la fenêtre de configuration des raccourcis et restaure les valeurs initiales
        si les changements n’ont pas été sauvegardés.
        """

        if not self._shortcuts_saved:
            self.keyboard_shortcut = self._initial_shortcut
            self.stop_keyboard_shortcut = self._initial_stop_shortcut
        self.root.attributes("-topmost", self.current_mode.mode.topmost)
        self.shortcut_window.destroy()

    def get_shortcut_start(self, event) -> None:
        """
        Capture la touche pressée pour définir le raccourci start/stop.

        Args:
            event: Événement clavier Tkinter.
        """

        key = self.map_key_name(event.keysym)

        if key != '??':
            self.keyboard_shortcut = key
            self.shortcut_entry.delete(0, tk.END)
            self.shortcut_entry.insert(0, self.keyboard_shortcut)

    def get_shortcut_stop(self, event) -> None:
        """
        Capture la touche pressée pour définir le raccourci stop transcription.

        Args:
            event: Événement clavier Tkinter.
        """

        key = self.map_key_name(event.keysym)

        if key != '??':
            self.stop_keyboard_shortcut = key
            self.stop_shortcut_entry.delete(0, tk.END)
            self.stop_shortcut_entry.insert(0, self.stop_keyboard_shortcut)

    def save_shortcuts(self) -> None:
        """
        Valide et enregistre les nouveaux raccourcis clavier définis.
        Met à jour le config, les hotkeys actifs, et ferme la fenêtre.
        """

        # Validation des deux raccourcis
        start_keys = self.keyboard_shortcut.split('+')
        stop_keys = self.stop_keyboard_shortcut.split('+')

        if not self.is_valid_shortcut(start_keys):
            messagebox.showerror("Raccourci invalide", "La combinaison pour démarrer/arrêter est invalide.")
            return

        if not self.is_valid_shortcut(stop_keys):
            messagebox.showerror("Raccourci invalide", "La combinaison pour arrêter la transcription est invalide.")
            return

        # Enregistrer les raccourcis clavier
        keyboard.clear_all_hotkeys()
        try:
            keyboard.add_hotkey(self.keyboard_shortcut, self.current_mode.toggle_start_stop)
            keyboard.add_hotkey(self.stop_keyboard_shortcut, self.current_mode.stop)
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'enregistrement des raccourcis : {e}")
            return

        # Mettre à jour le tooltip du bouton principal
        change_toolTip(self.current_mode.rec_button, self.keyboard_shortcut)

        # Sauvegarder immédiatement les raccourcis
        self.current_mode.app.config.shortcut = self.keyboard_shortcut
        self.current_mode.app.config.shortcut_stop = self.stop_keyboard_shortcut
        self.current_mode.app.config.save_config(self.root)

        # Marquer comme sauvegardé
        self._shortcuts_saved = True

        # Fermer la fenêtre
        self.on_close_shortcut_window()

    def is_valid_shortcut(self, keys: list[str]) -> bool:
        """
        Vérifie si une combinaison de touches représente un raccourci valide.

        Args:
            keys (list[str]): Liste des touches pressées.

        Returns:
            bool: True si la combinaison est valide, sinon False.
        """

        # Filtrer les touches inconnues
        keys = [k for k in keys if k != '??']
        if len(keys) == 1 and (keys[0].lower().startswith('f') and keys[0][1:].isdigit() or keys[0] == 'fn'):
            return True
        if len(keys) == 2 and ('ctrl' in keys or 'fn' in keys):
            return True  # Ctrl+quelque chose ou Fn+quelque chose
        if len(keys) == 3 and 'ctrl' in keys and 'shift' in keys:
            return True  # Ctrl+Shift+quelque chose
        if len(keys) == 3 and 'ctrl' in keys and 'alt' in keys:
            return True  # Alt+Ctrl+quelque chose
        if len(keys) == 3 and 'fn' in keys and 'ctrl' in keys:
            return True  # Fn+Ctrl+quelque chose
        if len(keys) == 4 and 'ctrl' in keys and 'alt' in keys and 'shift' in keys:
            return True  # Alt+Ctrl+Shift+quelque chose
        if len(keys) == 4 and 'fn' in keys and 'ctrl' in keys and 'shift' in keys:
            return True  # Fn+Ctrl+Shift+quelque chose
        if len(keys) == 5 and 'fn' in keys and 'ctrl' in keys and 'alt' in keys and 'shift' in keys:
            return True  # Fn+Alt+Ctrl+Shift+quelque chose
        return False

    def map_key_name(self, key: str) -> str:
        """
        Traduit les noms de touches complexes en noms standards (ex: Control_L → ctrl).

        Args:
            key (str): Nom de la touche.

        Returns:
            str: Nom mappé, ou la valeur originale si non reconnue.
        """

        key_mapping = {
            'Control_L': 'ctrl',
            'Control_R': 'ctrl',
            'Shift_L': 'shift',
            'Shift_R': 'shift',
            'Alt_L': 'alt',
            'Alt_R': 'alt',
            'Fn_L': 'fn',
            'Fn_R': 'fn',
            # Ajoutez d'autres mappages si nécessaire
        }
        return key_mapping.get(key, key)

    def on_key_press_start(self, event):
        key = self.map_key_name(event.keysym)
        if key not in self._pressed_keys:
            self._pressed_keys.append(key)
        combo = '+'.join(self._pressed_keys)
        self.shortcut_entry.delete(0, tk.END)
        self.shortcut_entry.insert(0, combo)
        self.keyboard_shortcut = combo

    def on_key_release_start(self, event):
        key = self.map_key_name(event.keysym)
        if key in self._pressed_keys:
            self._pressed_keys.remove(key)

    def on_key_press_stop(self, event):
        key = self.map_key_name(event.keysym)
        if key not in self._pressed_keys:
            self._pressed_keys.append(key)
        combo = '+'.join(self._pressed_keys)
        self.stop_shortcut_entry.delete(0, tk.END)
        self.stop_shortcut_entry.insert(0, combo)
        self.stop_keyboard_shortcut = combo

    def on_key_release_stop(self, event):
        key = self.map_key_name(event.keysym)
        if key in self._pressed_keys:
            self._pressed_keys.remove(key)
