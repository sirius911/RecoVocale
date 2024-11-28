import tkinter as tk
from tkinter import messagebox
from utils_window import change_toolTip
import keyboard


class ShortcutManager:
    def __init__(self, root, current_mode, keyboard_shortcut):
        self.root = root
        self.current_mode = current_mode
        self.keyboard_shortcut = keyboard_shortcut
        self.shortcut_window = None
        self.shortcut_entry = None

    def change_shortcut(self):
        self.root.attributes("-topmost", False)  # Désactiver l'attribut "toujours au-dessus"
        self.shortcut_window = tk.Toplevel(self.root)
        self.shortcut_window.title("Changer le raccourci clavier")
        self.shortcut_window.attributes("-topmost", True)  # S'assurer que la fenêtre est au-dessus

        tk.Label(self.shortcut_window, text="Appuyez sur une nouvelle combinaison de touches :").pack(pady=10)
        self.shortcut_entry = tk.Entry(self.shortcut_window)
        self.shortcut_entry.pack(pady=10)
        self.shortcut_entry.bind('<KeyPress>', self.get_shortcut)
        self.shortcut_entry.focus_set()

        # Réinitialiser self.keyboard_shortcut
        self.keyboard_shortcut = ''
        self.shortcut_entry.delete(0, tk.END)

        # Assurez-vous de réactiver "toujours au-dessus" lorsque la fenêtre est fermée
        self.shortcut_window.protocol("WM_DELETE_WINDOW", self.on_close_shortcut_window)

    def on_close_shortcut_window(self):
        self.root.attributes("-topmost", self.current_mode.mode.topmost)  # Réactiver l'attribut "toujours au-dessus"
        self.shortcut_window.destroy()

    def get_shortcut(self, event):
        key = self.map_key_name(event.keysym)

        if key == 'Return':  # Ignore the Enter key itself
            if self.is_valid_shortcut(self.keyboard_shortcut.split('+')):
                keyboard.clear_all_hotkeys()
                keyboard.add_hotkey(self.keyboard_shortcut, self.current_mode.toggle_start_stop)
                change_toolTip(self.current_mode.rec_button, self.keyboard_shortcut)
                self.on_close_shortcut_window()  # Fermer la fenêtre et réactiver "toujours au-dessus"
            else:
                messagebox.showerror("Raccourci invalide", "La combinaison de touches n'est pas valide.")
                self.keyboard_shortcut = ''  # Reset the pressed keys
                self.shortcut_entry.delete(0, tk.END)
            return

        current_keys = self.keyboard_shortcut.split('+') if self.keyboard_shortcut else []

        if key not in current_keys:
            current_keys.append(key)

        self.keyboard_shortcut = '+'.join(current_keys)
        self.shortcut_entry.delete(0, tk.END)
        self.shortcut_entry.insert(0, self.keyboard_shortcut)

    def is_valid_shortcut(self, keys):
        if len(keys) == 1 and (keys[0].startswith('F') or keys[0] == 'fn'):
            return True  # Touche de fonction seule ou Fn seule
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

    def map_key_name(self, key):
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
