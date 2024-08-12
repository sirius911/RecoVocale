from Mode import Mode
from utils_window import create_menus, create_buttons
from info import *

class ReduitMode(Mode):
    def enter(self):
        self.mode = ModeStyle.SMALL
        # self.root.resizable(False, False)
        self.app.simulate_keyboard = True
        self.ui()
        self.root.geometry(f"{WINDOW_WIDTH_SMALL}x{WINDOW_HEIGHT_SMALL}+{self.app.config.x_window}+{self.app.config.y_window}")
        # self.root.geometry("200x65")

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