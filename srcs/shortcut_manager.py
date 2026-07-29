import tkinter as tk
from tkinter import messagebox


class ShortcutManager:
    """Gère l'unique raccourci démarrer / arrêter de RecoVocale."""

    def __init__(self, root, app, keyboard_shortcut):
        """
        Args:
            root: Fenêtre principale Tkinter.
            app: Instance principale de RecoVocale.
            keyboard_shortcut (str): Raccourci principal démarrer / arrêter.
        """
        self.root = root
        self.app = app
        self.keyboard_shortcut = keyboard_shortcut
        self.shortcut_window = None
        self.shortcut_entry = None
        self._pressed_keys = []
        self._initial_shortcut = keyboard_shortcut
        self._shortcuts_saved = False

    def change_shortcut(self) -> None:
        """Ouvre la fenêtre permettant de modifier le raccourci principal."""
        if self.shortcut_window and self.shortcut_window.winfo_exists():
            self.shortcut_window.lift()
            self.shortcut_window.focus_force()
            return

        self._initial_shortcut = self.keyboard_shortcut
        self._shortcuts_saved = False
        self._pressed_keys.clear()

        # Le raccourci actif est suspendu pendant sa saisie afin qu'il ne
        # déclenche pas la transcription dans la fenêtre de configuration.
        self.app.unregister_keyboard_shortcut()

        self.root.attributes("-topmost", False)
        self.shortcut_window = tk.Toplevel(self.root)
        self.shortcut_window.title("Changer le raccourci clavier")
        self.shortcut_window.attributes("-topmost", True)
        self.shortcut_window.resizable(False, False)

        tk.Label(
            self.shortcut_window,
            text="Raccourci démarrer / arrêter :"
        ).pack(padx=20, pady=(15, 5))

        self.shortcut_entry = tk.Entry(self.shortcut_window, justify="center")
        self.shortcut_entry.pack(padx=20, pady=(0, 10))
        self.shortcut_entry.insert(0, self.keyboard_shortcut or "")
        self.shortcut_entry.bind("<KeyPress>", self.on_key_press_start)
        self.shortcut_entry.bind("<KeyRelease>", self.on_key_release_start)
        self.shortcut_entry.bind("<FocusIn>", lambda _event: self._pressed_keys.clear())
        self.shortcut_entry.focus_set()

        tk.Button(
            self.shortcut_window,
            text="Enregistrer",
            command=self.save_shortcuts
        ).pack(pady=(0, 15))

        self.shortcut_window.protocol(
            "WM_DELETE_WINDOW",
            self.on_close_shortcut_window
        )

    def on_close_shortcut_window(self) -> None:
        """Ferme la fenêtre et restaure l'ancien raccourci en cas d'annulation."""
        if not self._shortcuts_saved:
            self.keyboard_shortcut = self._initial_shortcut
            try:
                self.app.register_keyboard_shortcut(self.keyboard_shortcut)
            except Exception as exc:
                messagebox.showerror(
                    "Erreur",
                    f"Impossible de restaurer le raccourci clavier : {exc}"
                )

        current_mode = getattr(self.app, "current_mode", None)
        mode_options = getattr(current_mode, "mode", None)
        topmost = getattr(mode_options, "topmost", True)
        self.root.attributes("-topmost", topmost)

        if self.shortcut_window and self.shortcut_window.winfo_exists():
            self.shortcut_window.destroy()
        self.shortcut_window = None
        self.shortcut_entry = None
        self._pressed_keys.clear()

    def save_shortcuts(self) -> None:
        """Valide, applique et sauvegarde immédiatement le nouveau raccourci."""
        from utils_window import change_toolTip

        shortcut = (self.keyboard_shortcut or "").strip()
        keys = shortcut.split("+") if shortcut else []

        if not self.is_valid_shortcut(keys):
            messagebox.showerror(
                "Raccourci invalide",
                "La combinaison pour démarrer / arrêter est invalide."
            )
            return

        try:
            # Cette méthode remplace immédiatement l'ancien raccourci par le nouveau.
            self.app.register_keyboard_shortcut(shortcut)
        except Exception as exc:
            # En cas d'échec, l'ancien raccourci reste utilisable.
            try:
                self.app.register_keyboard_shortcut(self._initial_shortcut)
            except Exception:
                pass
            messagebox.showerror(
                "Erreur",
                f"Erreur lors de l'enregistrement du raccourci : {exc}"
            )
            return

        self.keyboard_shortcut = shortcut

        current_mode = getattr(self.app, "current_mode", None)
        rec_button = getattr(current_mode, "rec_button", None)
        if rec_button is not None:
            change_toolTip(rec_button, shortcut)

        self.app.config.shortcut = shortcut
        self.app.config.save_config(self.root)

        self._shortcuts_saved = True
        self.on_close_shortcut_window()
        self.app.info()

    def is_valid_shortcut(self, keys: list[str]) -> bool:
        """Vérifie si une combinaison de touches est acceptée."""
        keys = [key.lower() for key in keys if key and key != "??"]

        if len(keys) == 1:
            key = keys[0]
            return key.startswith("f") and key[1:].isdigit()

        if len(keys) == 2 and ("ctrl" in keys or "fn" in keys):
            return True
        if len(keys) == 3 and "ctrl" in keys and "shift" in keys:
            return True
        if len(keys) == 3 and "ctrl" in keys and "alt" in keys:
            return True
        if len(keys) == 3 and "fn" in keys and "ctrl" in keys:
            return True
        if len(keys) == 4 and {"ctrl", "alt", "shift"}.issubset(keys):
            return True
        if len(keys) == 4 and {"fn", "ctrl", "shift"}.issubset(keys):
            return True
        if len(keys) == 5 and {"fn", "ctrl", "alt", "shift"}.issubset(keys):
            return True
        return False

    def map_key_name(self, key: str) -> str:
        """Convertit les noms Tkinter en noms compris par le module keyboard."""
        key_mapping = {
            "Control_L": "ctrl",
            "Control_R": "ctrl",
            "Shift_L": "shift",
            "Shift_R": "shift",
            "Alt_L": "alt",
            "Alt_R": "alt",
            "Fn_L": "fn",
            "Fn_R": "fn",
        }
        return key_mapping.get(key, key).lower()

    def on_key_press_start(self, event):
        key = self.map_key_name(event.keysym)
        if key != "??" and key not in self._pressed_keys:
            self._pressed_keys.append(key)

        combo = "+".join(self._pressed_keys)
        self.shortcut_entry.delete(0, tk.END)
        self.shortcut_entry.insert(0, combo)
        self.keyboard_shortcut = combo
        return "break"

    def on_key_release_start(self, event):
        key = self.map_key_name(event.keysym)
        if key in self._pressed_keys:
            self._pressed_keys.remove(key)
        return "break"
