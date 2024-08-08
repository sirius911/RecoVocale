from Mode import Mode
import tkinter as tk

class ReduitMode(Mode):
    def enter(self):
        self.ui()

    def ui(self):
        self.app.button_frame = tk.Frame(self.root)
        self.app.button_frame.pack(pady=10)

        self.app.start_button = tk.Button(self.app.button_frame, text="Start", command=self.app.start_client)
        self.app.start_button.pack(side=tk.LEFT, padx=5, pady=10)

        self.app.stop_button = tk.Button(self.app.button_frame, text="Stop", command=self.app.stop_client)
        self.app.stop_button.pack(side=tk.RIGHT, padx=5, pady=10)
        
        self.app.status_label = tk.Label(self.root, text="Server status: Unknown", fg="blue")
        self.app.status_label.pack(pady=10)

    def exit(self):
        for widget in self.root.winfo_children():
            widget.destroy()
