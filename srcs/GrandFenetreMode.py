from Mode import Mode
import tkinter as tk
from utils_window import create_menus, create_buttons
from info import *



class GrandFenetreMode(Mode):
    def enter(self):
        self.mode = ModeStyle.BIG
        self.root.resizable(True, True)
        self.ui()
        self.root.geometry(f"{WINDOW_WIDTH_BIG}x{WINDOW_HEIGHT_BIG}+{self.app.config.x_window}+{self.app.config.y_window}")
        # self.root.geometry("940x709")

    def ui(self):
        create_menus(self)
        create_buttons(self)
           
        self.valide_button = tk.Button(self.root, text=f"Validation", command=self.app.valid_transcriptions)
        self.valide_button.pack(side=tk.RIGHT,pady=10)
        #------------------------------------------------------------------------------

        self.simulate_keyboard_var = tk.BooleanVar()
        self.simulate_keyboard_check = tk.Checkbutton(self.root,
                                                      text="Simule Touches Clavier",
                                                      variable=self.simulate_keyboard_var,
                                                      command=self.update_simulate_keyboard
                                                      )
        self.simulate_keyboard_check.pack(pady=10)
        # Synchronisation initiale avec la variable booléenne
        self.simulate_keyboard_var.set(self.app.simulate_keyboard)

        self.text_box_frame = tk.Frame(self.root)
        self.text_box_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
        self.text_box_scrollbar = tk.Scrollbar(self.text_box_frame)
        self.text_box_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.text_box = tk.Text(self.text_box_frame, yscrollcommand=self.text_box_scrollbar.set)
        self.text_box.pack(pady=10, fill=tk.BOTH, expand=True)
        
        self.text_box_scrollbar.config(command=self.text_box.yview)
        self.copy_button = tk.Button(self.root, text="Copy", command=self.copy_to_clipboard)
        self.copy_button.pack(pady=10)

        self.clear_text_box_button = tk.Button(self.root, text="Clear", command=self.clear_text_box)
        self.clear_text_box_button.pack(pady=10)

        # self.monitor_label = tk.Label(self.root, text="Monitoring du micro")
        # self.monitor_label.pack()

        # self.monitor_frame = tk.Frame(self.root)
        # self.monitor_frame.pack(pady=10)

        # self.rec_canvas = tk.Canvas(self.monitor_frame, width=20, height=20)
        # self.rec_circle = self.rec_canvas.create_oval(2, 2, 18, 18, fill="grey")
        # self.rec_canvas.pack(side=tk.LEFT, padx=5)

        # self.monitor_gauge = tk.Canvas(self.monitor_frame, width=300, height=20, bg="white")
        # self.monitor_gauge.pack(side=tk.LEFT, padx=5)

        # self.status_frame = tk.Frame(self.root)
        # self.status_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)

        # self.status_label = tk.Label(self.status_frame, text="Checking server status...")
        # self.status_label.pack(side=tk.LEFT, padx=(0, 5))

        # self.status_error = tk.Label(self.status_frame, text="", fg="red")
        # self.status_error.pack(side=tk.RIGHT, padx=(5, 0))

    # def toggle_record(self):
    #     if self.app.recording:
    #         self.app.pause()  # Call pause function
    #     else:
    #         self.app.unpause()  # Call unpause function

    # def load_and_resize_image(self, path, size):
    #     image = Image.open(path)
    #     image = image.resize(size, Image.LANCZOS)  # Use LANCZOS for high-quality downsizing
    #     return ImageTk.PhotoImage(image)


    def update_simulate_keyboard(self):
        self.app.simulate_keyboard = self.simulate_keyboard_var.get()
        if self.app.simulate_keyboard:
            self.app.simulator_keyboard.init()

    # def update_rec_circle(self):
    #     fill = 'red' if self.app.recording else 'grey'
    #     self.rec_canvas.itemconfig(self.rec_circle, fill=fill)

    # def update_image_button(self):
    #     if self.app.recording:
    #         self.rec_button.config(image=self.record_image)
    #     else:
    #         self.rec_button.config(image=self.pause_image)

    # def update_micro_menu(self):
    #     self.micro_menu.delete(0, tk.END)
    #     self.micro_list = []
    #     for i in range(self.app.audio.get_device_count()):
    #         dev = self.app.audio.get_device_info_by_index(i)
    #         if dev['maxInputChannels'] > 0:
    #             channels = dev['maxInputChannels']
    #             self.micro_list.append((dev['index'], dev['name'], channels))

    #     for idx, name, channels in self.micro_list:
    #         self.micro_menu.add_radiobutton(label=f"{name} (ID: {idx}, Channels: {channels})",
    #                                         command=lambda idx=idx: self.select_micro(idx))
    
    #     # Check the default microphone
    #     if self.app.selected_micro is not None:
    #         self.micro_menu.invoke(self.app.selected_micro)

    # def select_micro(self, idx):
    #     self.selected_micro = idx
    #     # self.app.update_mic_stream()

    def copy_to_clipboard(self):
        """
        Copy the content of the text box to the clipboard.
        """
        self.root.clipboard_clear()
        self.root.clipboard_append(self.text_box.get("1.0", tk.END))
        self.root.update()

    def clear_text_box(self):
        """
        Clear the content of the text box.
        """
        self.app.valid_transcriptions()
        self.app.last_transcriptions = ""
        self.text_box.delete('1.0', tk.END)
        self.root.update()

    def exit(self):
        # pour le switch mode
        for widget in self.root.winfo_children():
            widget.destroy()

    # def update_monitoring(self):
    #     try:
    #         data = self.app.stream.read(1024, exception_on_overflow=False)
    #         audio_level = np.frombuffer(data, dtype=np.int16)
    #         audio_level = np.abs(audio_level).mean()
    #         self.monitor_gauge.delete("all")
    #         self.monitor_gauge.create_rectangle(0, 0, min(audio_level * 300 /2500, 300), 20, fill="green")
    #         self.update_icon_image(self.create_image(audio_level))
            
    #     except OSError as e:
    #         self.status_error.config(text="Erreur de lecture", fg="red")
    #         self.monitor_gauge.delete("all")
    #         self.monitor_gauge.create_rectangle(0, 0, 300, 20, fill="red")
    #         self.update_icon_image(self.create_error_image())

    # def update_status(self):
    #     super().update_status()
    #     text = 'Server status: Connected' if self.app.status_server else 'Server status: Not connected'
    #     self.status_label.config(text=text)

    def update_transcription(self, transcriptions):
        # print(f"dans update_transcription({transcriptions})")

        self.text_box.delete('1.0', tk.END)
        self.text_box.insert(tk.END, self.app.last_transcriptions)
        self.text_box.insert(tk.END, transcriptions)
        # for line in transcriptions:
        #     self.text_box.insert(tk.END, line + '\n')
        # Scroll to the end
        self.text_box.see(tk.END)
        # return self.text_box.get('1.0', tk.END).strip()