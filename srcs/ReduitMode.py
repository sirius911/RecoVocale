from Mode import Mode
from utils_window import create_menus, create_buttons
from info import SMALL

class ReduitMode(Mode):
    def enter(self):
        self.mode = SMALL
        # self.app.simulate_keyboard = SMALL.simule_keyboard
        self.mod_var.set(SMALL)
        self.ui()
        self.client_manager = None
        super().enter()

    def ui(self):
        create_menus(self)
        create_buttons(self)

        # self.app.status_label = tk.Label(self.root, text="Server status: Unknown", fg="blue")
        # self.app.status_label.pack(pady=10)

    def start(self):
        print("START")

    def stop(self):
        print("STOP")

    def pause(self):
        print("PAUSE")
        self.app.recording = False
        self.update()

    def unpause(self):
        print("UNPAUSE")
        self.app.recording = True
        self.update()

    # def exit(self):
    #     for widget in self.root.winfo_children():
    #         widget.destroy()
    
    def valid_transcriptions(self):
        pass

    def update_transcription(self, message):
        pass