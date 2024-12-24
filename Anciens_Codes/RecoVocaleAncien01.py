import time
import tkinter as tk
from tkinter import messagebox
import threading
import pyaudio
import numpy as np
from client import EnhancedTranscriptionClient
from Correcteur import Correcteur
import socket
from pynput.keyboard import Controller, Key
import ctypes  # Import ctypes to interact with the Windows API
import keyboard
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw
from PhilipsMic import PhilipsMic  # Import the PhilipsMic class

SERVEUR_IP = "10.1.11.215"
PORT = 9090
VERSION = "0.5"
SHORTCUT = "F3"

class TranscriptionApp:
    def __init__(self, root):
        """
        Initialize the TranscriptionApp with the given root window.
        
        Args:
            root (tk.Tk): The root window for the Tkinter application.
        """
        self.root = root
        # self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
        self.is_hidden = False

        self.root.title(f"RecoVocale [{SERVEUR_IP}:{PORT}] (v{VERSION})")
        self.root.attributes("-topmost", True)  # Keep the window on top of others

        self.host = SERVEUR_IP
        self.port = PORT
        self.lang = "fr"
        self.model = "small"
        self.translate = False
        self.use_vad = True
        self.save_output_recording = False
        self.output_recording_filename = "./output_recording.wav"

        self.client = None
        self.client_thread = None
        self.running = False
        self.status_server = False
        self.previous_text = ""
        self.last_transcription = ""
        self.new_transcription = False

        self.correcteur = Correcteur("corrections.json")

        self.stream = None
        try:
            self.audio = pyaudio.PyAudio()
            self.selected_micro = self.audio.get_default_input_device_info()["index"]
            self.check_micro = True
        except OSError:
            print("Pas de micro ...")
            self.selected_micro = None
            self.check_micro = False

        self.simulate_keyboard = False

        self.keyboard_shortcut = SHORTCUT

        self.current_mode = GrandFenetreMode(self)
        # self.ui()

        self.update_mic_stream()

        self.check_server_status()
        self.update_monitoring()

        # Initialize the keyboard controller
        self.keyboard = Controller()
        
        # Minimize the console window
        # self.minimize_console()

        # Register global hotkeys
        
        keyboard.add_hotkey(self.keyboard_shortcut, self.toggle_start_stop)

        # Initialize PhilipsMic
        self.mic = PhilipsMic(self.start_client, self.stop_client)

    # def create_menus(self):
    #     self.menu_bar = tk.Menu(self.root)
    #     self.root.config(menu=self.menu_bar)

    #     self.settings_menu = tk.Menu(self.menu_bar, tearoff=0)
    #     self.menu_bar.add_cascade(label="Paramètres", menu=self.settings_menu)

    #     self.micro_menu = tk.Menu(self.settings_menu, tearoff=0)
    #     self.settings_menu.add_cascade(label="Micro", menu=self.micro_menu)

    #     self.update_micro_menu()

    #     self.settings_menu.add_command(label="Raccourci Clavier", command=self.change_shortcut)

    # def update_micro_menu(self):
    #     self.micro_menu.delete(0, tk.END)
    #     self.micro_list = []
    #     for i in range(self.audio.get_device_count()):
    #         dev = self.audio.get_device_info_by_index(i)
    #         if dev['maxInputChannels'] > 0:
    #             channels = dev['maxInputChannels']
    #             self.micro_list.append((dev['index'], dev['name'], channels))

    #     for idx, name, channels in self.micro_list:
    #         self.micro_menu.add_radiobutton(label=f"{name} (ID: {idx}, Channels: {channels})",
    #                                         command=lambda idx=idx: self.select_micro(idx))
    
    #     # Check the default microphone
    #     if self.selected_micro is not None:
    #         self.micro_menu.invoke(self.selected_micro)

    def select_micro(self, idx):
        self.selected_micro = idx
        self.update_mic_stream()

    # def ui(self):
    #     """
    #     Set up the user interface components for the TranscriptionApp.
    #     """

    #     # Create a frame to hold the start and stop buttons
    #     self.button_frame = tk.Frame(self.root)
    #     self.button_frame.pack(pady=10)

    #     self.start_button = tk.Button(self.button_frame, text=f"Start ({SHORTCUT})", command=self.start_client)
    #     self.start_button.pack(side=tk.LEFT, padx=5, pady=10)

    #     self.stop_button = tk.Button(self.button_frame, text=f"Stop ({SHORTCUT})", command=self.stop_client)
    #     self.stop_button.pack(side=tk.RIGHT, padx=5, pady=10)

    #     self.simulate_keyboard_var = tk.BooleanVar()
    #     self.simulate_keyboard_check = tk.Checkbutton(root, text="Simule Keyboard", variable=self.simulate_keyboard_var)
    #     self.simulate_keyboard_check.pack(pady=10)

    #     self.text_box_frame = tk.Frame(self.root)
    #     self.text_box_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
    #     self.text_box_scrollbar = tk.Scrollbar(self.text_box_frame)
    #     self.text_box_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
    #     self.text_box = tk.Text(self.text_box_frame, yscrollcommand=self.text_box_scrollbar.set)
    #     self.text_box.pack(pady=10, fill=tk.BOTH, expand=True)
        
    #     self.text_box_scrollbar.config(command=self.text_box.yview)
    #     self.copy_button = tk.Button(root, text="Copy", command=self.copy_to_clipboard)
    #     self.copy_button.pack(pady=10)

    #     self.clear_text_box_button = tk.Button(root, text="Clear", command=self.clear_text_box)
    #     self.clear_text_box_button.pack(pady=10)

    #     self.monitor_label = tk.Label(root, text="Monitoring du micro")
    #     self.monitor_label.pack()

    #     self.monitor_frame = tk.Frame(root)
    #     self.monitor_frame.pack(pady=10)

    #     self.rec_canvas = tk.Canvas(self.monitor_frame, width=20, height=20)
    #     self.rec_circle = self.rec_canvas.create_oval(2, 2, 18, 18, fill="grey")
    #     self.rec_canvas.pack(side=tk.LEFT, padx=5)

    #     self.monitor_gauge = tk.Canvas(self.monitor_frame, width=300, height=20, bg="white")
    #     self.monitor_gauge.pack(side=tk.LEFT, padx=5)

    #     # Create a frame to hold the status labels
    #     self.status_frame = tk.Frame(self.root)
    #     self.status_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)

    #     self.status_label = tk.Label(self.status_frame, text="Checking server status...")
    #     self.status_label.pack(side=tk.LEFT, padx=(0, 5))  # Slightly offset to the left

    #     self.status_error = tk.Label(self.status_frame, text="", fg="red")
    #     self.status_error.pack(side=tk.RIGHT, padx=(5, 0))  # Slightly offset to the right

    #     self.create_menus()
    #     # Initialize system tray icon
    #     self.create_systray_icon()

    #     # Add this line to start the application in the background
    #     self.hide_window()

    def update_mic_stream(self):
        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()

            if self.selected_micro is not None:
                dev_info = self.audio.get_device_info_by_index(self.selected_micro)
                sample_rate = int(dev_info['defaultSampleRate'])

                self.stream = self.audio.open(format=pyaudio.paInt16,
                                            channels=1,  # Force mono input
                                            rate=sample_rate,
                                            input=True,
                                            input_device_index=self.selected_micro,
                                            output=False,
                                            frames_per_buffer=1024)
            else:
                self.stream = self.audio.open(format=pyaudio.paInt16,
                                            channels=1,  # Force mono input
                                            rate=16000,
                                            input=True,
                                            output=False,
                                            frames_per_buffer=1024)
            # self.status_error.config(text="")
        except OSError as e:
            print(f"Error opening stream: {e}")
            self.status_error.config(text="Erreur de lecture micro")
            self.stream = None
            self.update_icon_image(self.create_error_image())

    def minimize_console(self):
        """
        Minimize the console window.
        """
        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32
        hWnd = kernel32.GetConsoleWindow()
        if hWnd:
            user32.ShowWindow(hWnd, 6)  # SW_MINIMIZE = 6

    def check_server_status(self):
        """
        Check the server status and update the UI accordingly.
        """
        try:
            sock = socket.create_connection((self.host, self.port), timeout=2)
            sock.close()
            self.status_server = True
            self.status_label.config(text="Server status: Connected", fg="green")
            self.start_button.config(state=tk.NORMAL)
            self.icon.title = f"RecoVocale (v{VERSION})[{self.keyboard_shortcut}] Connected"
        except (socket.timeout, ConnectionRefusedError, socket.gaierror, OSError):
            self.status_label.config(text=f"Server status: Not Connected", fg="red")
            self.start_button.config(state=tk.DISABLED)
            self.icon.title = f"RecoVocale (v{VERSION})[{self.keyboard_shortcut}] not Connected"
            self.root.after(2000, self.check_server_status)  # Check every 2 seconds


    def create_client(self):
        """
        Create and return an instance of EnhancedTranscriptionClient.
        
        Returns:
            EnhancedTranscriptionClient: The created transcription client instance.
        """
        return EnhancedTranscriptionClient(
            self.host,
            self.port,
            lang=self.lang,
            model=self.model,
            translate=self.translate,
            use_vad=self.use_vad,
            save_output_recording=self.save_output_recording,
            output_recording_filename=self.output_recording_filename
        )

    def start_client_thread(self):
        """
        Start the client thread.
        """
        self.client()

    def start_client(self):
        """
        Start the transcription client and update the UI.
        """
        if not self.status_server or not self.check_micro:  # TODO plutot utiliser une fonction get_status_server() qui verifie que le serveur est toujours actif
            return
        if self.client_thread and self.client_thread.is_alive():
            self.stop_client()

        self.client = self.create_client()
        self.running = True
        self.start_button.config(state = tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.client_thread = threading.Thread(target=self.start_client_thread)
        self.client_thread.start()
        self.new_transcription = True
        self.previous_text = ""
        self.update_transcriptions()
        if not self.is_hidden:
            self.rec_canvas.itemconfig(self.rec_circle, fill="red")  # Light up the red circle when the thread is running
        # Update the systray icon to red
        # self.update_icon_image(self.create_red_image(64, 64))

    def stop_client(self):
        """
        Stop the transcription client and update the UI.
        """
        if not self.status_server: # TODO plutot utiliser une fonction get_status_server() qui verifie que le serveur est toujours actif
            return
        self.running = False
        if self.client:
            self.client.stop()
        if self.client_thread:
            self.client_thread.join()
            self.client_thread = None
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        if not self.is_hidden:
            self.rec_canvas.itemconfig(self.rec_circle, fill="grey")  # Turn off the red circle when the thread is stopped
        # Update the systray icon to black and white
        # self.update_icon_image(self.create_image(64, 64, "black", "white"))

    def on_closing(self):
        """
        Handle the window closing event.
        """
        if self.client:
            self.client.stop()
        if self.client_thread:
            self.client_thread.join()
            self.client_thread = None
        self.root.destroy()

    def update_transcriptions(self):
        """
        Update the transcriptions in the text box every 500ms.
        """
        if self.running:
            transcriptions, phrase_finished =self.client.get_transcriptions()
            transcriptions = transcriptions if self.client else []
            corrected_transcriptions = [self.correcteur.applique_corrections(line) for line in transcriptions]
            combined_text = ' '.join(corrected_transcriptions)
            if combined_text != "":
                self.text_box.delete('1.0', tk.END)
                self.text_box.insert(tk.END, self.last_transcription)
                for line in corrected_transcriptions:
                    self.text_box.insert(tk.END, line + '\n')

                # Scroll to the end
                self.text_box.see(tk.END)

                if self.simulate_keyboard_var.get():
                    self.animate_typing(combined_text)
                
                if phrase_finished:
                    self.last_transcription = self.text_box.get('1.0', tk.END).strip()
                    self.start_client()
                else:
                    self.root.after(500, self.update_transcriptions)
            else:
                self.root.after(500, self.update_transcriptions)
            
    def update_monitoring(self):
        if self.stream:
            try:
                data = self.stream.read(1024, exception_on_overflow=False)
                audio_level = np.frombuffer(data, dtype=np.int16)
                audio_level = np.abs(audio_level).mean()
                self.update_icon_image(self.create_image(audio_level))
                if not self.is_hidden:
                    self.monitor_gauge.delete("all")
                    self.monitor_gauge.create_rectangle(0, 0, min(audio_level * 300 /2500, 300), 20, fill="green")
                # self.status_error.config(text="", fg="red")
            except OSError as e:
                # print(f"Error reading from stream: {e}")
                # self.status_error.config(text="Erreur de lecture", fg="red")
                self.monitor_gauge.delete("all")
                self.monitor_gauge.create_rectangle(0, 0, 300, 20, fill="red")
                self.update_icon_image(self.create_error_image())

        self.root.after(100, self.update_monitoring)

    def animate_typing(self, new_text:str):
        """
        Simulate typing to display new_text at the cursor position.
        
        Args:
            new_text (str): The text to type out.
        """
        def find_common_prefix(s1, s2): 
            common_prefix_length = 0
            for c1, c2 in zip(s1, s2):
                if c1 != c2:
                    break
                common_prefix_length += 1
            return common_prefix_length
        
        common_prefix_length = find_common_prefix(self.previous_text, new_text)
        # Erase the incorrect part
        for _ in range(len(self.previous_text) - common_prefix_length):
            self.keyboard.press(Key.backspace)
            self.keyboard.release(Key.backspace)
            time.sleep(0.02)

        new_part = new_text[common_prefix_length:]
        # Type the new part
        for char in new_part:
            self.type_character(char)
            time.sleep(0.02)  # Add a small delay to simulate typing speed
        
        self.previous_text = new_text

    def type_character(self, char:str):
        """
        Type a single character using the keyboard controller.
        
        Args:
            char (str): The character to type.
        """
        if char == '\n':
            self.keyboard.press(Key.enter)
            self.keyboard.release(Key.enter)
        elif char == ' ':
            self.keyboard.press(Key.space)
            self.keyboard.release(Key.space)
        elif char == '\t':
            self.keyboard.press(Key.tab)
            self.keyboard.release(Key.tab)
        else:
            self.keyboard.type(char)

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
        self.text_box.delete('1.0', tk.END)
        self.last_transcription = ""
        self.previous_text = ""
        self.root.update()

    def toggle_start_stop(self):
        """
        Toggle the start/stop state of the transcription client.
        """
        if self.running:
            self.stop_client()
        else:
            self.start_client()
    
#---------------------------------------------------------------------------------------------------------------------
#               Arrière plan a détacher dans une autre class    
    def create_image(self, niveau:int):
        """
        Creates a 64x64 image with a rectangle of specified color and height.

        Parameters:
        self (object): A reference to the instance of the class.
        niveau (int): The height of the rectangle as a percentage of 64 pixels.
        record (int): True if the client is recording 
        Returns:
        Image: The generated image with the colored rectangle.
        """
        # Create a 64x64 pixel image with a white background
        img = Image.new('RGB', (64, 64), "white")
        draw = ImageDraw.Draw(img)
        if self.running:
            # Dessiner un cercle rouge au centre
            draw.ellipse((16, 16, 48, 48), fill="red")
        else:
            # Calculate the height of the rectangle to be drawn
            height = int(niveau / 2000 * 64)

            # Draw the rectangle with the specified color
            draw.rectangle([0, 64 - height, 64, 64], fill="blue")

        return img

    def create_error_image(self):
        # Create a 64x64 pixel image with a white background
        img = Image.new('RGB', (64, 64), "white")
        draw = ImageDraw.Draw(img)

        # Draw the first diagonal line from top-left to bottom-right
        draw.line((0, 0, 64, 64), fill="red", width=10)

        # Draw the second diagonal line from top-right to bottom-left
        draw.line((64, 0, 0, 64), fill="red", width=10)

        return img
    
    def update_icon_image(self, image):
        self.icon.icon = image
        # self.icon.update_icon()
    
    def create_systray_icon(self):
        self.icon = pystray.Icon("RecoVocale")
        self.icon.icon = self.create_image(50)
        self.icon.menu = pystray.Menu(
            item('Show', self.show_window),
            item('Raccourci Clavier', self.change_shortcut),
            item('Exit', self.exit_app)
        )
        self.icon.run_detached()
        self.icon.title = f"RecoVocale (v{VERSION})[{self.keyboard_shortcut}]"

    def show_window(self, icon, item):
        self.simulate_keyboard_var.set(False)
        self.root.deiconify()
        self.is_hidden = False

    def hide_window(self):
        self.simulate_keyboard_var.set(True)
        self.root.withdraw()
        self.is_hidden = True

    def exit_app(self, icon, item):
        self.icon.stop()
        self.root.quit()

#---------------------------------------------------------------------------------------------------------------------
#               Fenetre shorcut a détacher dans une autre class 
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
        self.root.attributes("-topmost", True)  # Réactiver l'attribut "toujours au-dessus"
        self.shortcut_window.destroy()

    def get_shortcut(self, event):
        key = self.map_key_name(event.keysym)

        if key == 'Return':  # Ignore the Enter key itself
            if self.is_valid_shortcut(self.keyboard_shortcut.split('+')):
                keyboard.clear_all_hotkeys()
                keyboard.add_hotkey(self.keyboard_shortcut, self.toggle_start_stop)
                self.start_button.config(text=f"Start ({self.keyboard_shortcut})")
                self.stop_button.config(text=f"Stop ({self.keyboard_shortcut})")
                self.icon.title = f"RecoVocale (v{VERSION})[{self.keyboard_shortcut}]"
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
        if len(keys) == 1 and keys[0].startswith('F'):
            return True  # Touche de fonction seule
        if len(keys) == 2 and 'ctrl' in keys:
            return True  # Ctrl+quelque chose
        if len(keys) == 3 and 'ctrl' in keys and 'shift' in keys:
            return True  # Ctrl+Shift+quelque chose
        if len(keys) == 3 and 'ctrl' in keys and 'alt' in keys:
            return True  # Alt+Ctrl+quelque chose
        if len(keys) == 4 and 'ctrl' in keys and 'alt' in keys and 'shift' in keys:
            return True  # Alt+Ctrl+Shift+quelque chose
        return False


    def map_key_name(self, key):
        key_mapping = {
            'Control_L': 'ctrl',
            'Control_R': 'ctrl',
            'Shift_L': 'shift',
            'Shift_R': 'shift',
            'Alt_L': 'alt',
            'Alt_R': 'alt'
            # Ajoutez d'autres mappages si nécessaire
        }
        return key_mapping.get(key, key)
#---------------------------------------------------------------------------------------------------------------------


if __name__ == "__main__":
    root = tk.Tk()
    app = TranscriptionApp(root)
    root.mainloop()
