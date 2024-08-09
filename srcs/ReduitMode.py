from Mode import Mode
import tkinter as tk
from utils_window import create_menus, create_buttons
from info import ModeStyle


class ReduitMode(Mode):
    def enter(self):
        self.mode = ModeStyle.SMALL
        self.app.simulate_keyboard = True
        self.ui()
        self.root.geometry("120x60")

    def ui(self):
        create_menus(self)
        create_buttons(self)
        
        # self.app.status_label = tk.Label(self.root, text="Server status: Unknown", fg="blue")
        # self.app.status_label.pack(pady=10)

    def exit(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def update_transcription(self, message):
        pass