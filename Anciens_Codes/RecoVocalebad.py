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

from pystray import MenuItem as item
from PIL import Image, ImageDraw
from PhilipsMic import PhilipsMic  # Import the PhilipsMic class
from info import *
from GrandFenetreMode import GrandFenetreMode
from ReduitMode import ReduitMode
from ArrierePlanMode import ArrierePlanMode

class TranscriptionApp:
    def __init__(self, root):
        """
        Initialize the TranscriptionApp with the given root window.
        
        Args:
            root (tk.Tk): The root window for the Tkinter application.
        """
        self.root = root
        # self.root.protocol("WM_DELETE_WINDOW", self.exit_program)
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
        self.recording = False
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
        self.mic = PhilipsMic(self.record, self.pause)

        self.start_client()

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
            
        except OSError as e:
            print(f"Error opening stream: {e}")
            self.stream = None
            self.current_mode.update_status(text="Erreur de lecture micro")

    def minimize_console(self):
        """
        Minimize the console window.
        """
        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32
        hWnd = kernel32.GetConsoleWindow()
        if hWnd:
            user32.ShowWindow(hWnd, 6)  # SW_MINIMIZE = 6

    def check_statut_client(self):
        self.status_server =  self.client.is_recording()
        self.current_mode.update_status()
        if not self.status_server:
            self.check_server_status()


    def check_server_status(self):
        """
        Check the server status and update the UI accordingly.
        """
        try:
            sock = socket.create_connection((self.host, self.port), timeout=2)
            sock.close()
            self.status_server = True
            self.current_mode.update_status()
        except (socket.timeout, ConnectionRefusedError, socket.gaierror, OSError):
            self.status_server = False
            self.current_mode.update_status()
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
        if not self.status_server or not self.check_micro:
            self.running = False
            self.recording = False
            return
        
        if self.client is not None:
            if self.client_thread and self.client_thread.is_alive():
                self.stop_client()
            self.client = self.create_client()
            self.client.set_pause(False)
            self.client_thread = threading.Thread(target=self.start_client_thread)
            self.client_thread.start()
            self.running = True
            self.recording = False
            self.client.set_pause(True)
        else:
            print("Client déjà crée")
        #     self.client.set_pause(False)
        # self.new_transcription = True
        # self.previous_text = ""
        # self.running = True
        # self.update_transcriptions()

    def record(self):
        self.recording = True
        self.client.set_pause(False)
        self.new_transcription = True
        self.previous_text = ""
        # self.running = True
        self.update_transcriptions()

    def pause(self):
        self.recording = False
        self.client.set_pause(True)
        self.update_transcriptions()

    # def start_stream(self):
    #     '''
    #         start pour le PhilipsSpeechMike pro
    #     '''
    #     if not self.status_server or not self.check_micro:
    #         return
    #     if not self.client:
    #          self.client = self.create_client()
    #          self.client_thread = threading.Thread(target=self.start_client_thread)
    #     self.running = True
    #     self.new_transcription = True
    #     self.previous_text = ""
    #     self.stream.start_stream()
    #     self.update_transcriptions()

    # def stop_stream(self):
    #     '''
    #         stop pour le PhilipsSpeechMike pro
    #     '''
    #     self.stream.stop_stream()
    #     self.running = False

    # def kill_client(self):
    #     if not self.status_server:
    #         return
    #     self.running = False
    #     if self.client:
    #         self.client.stop()
    #     if self.client_thread:
    #         self.client_thread.join()
    #         self.client_thread = None

    def stop_client(self):
        """
        Stop the transcription client and update the UI.
        """
        if not self.status_server:
            return
        self.running = False
        self.client.set_pause(True)
        self.update_transcriptions()
        if self.client:
            self.client.stop()
            self.client = None
        if self.client_thread:
            self.client_thread.join()
            self.client_thread = None
        # # self.start_button.config(state=tk.NORMAL)
        # self.stop_button.config(state=tk.DISABLED)
        # if not self.is_hidden:
        #     self.rec_canvas.itemconfig(self.rec_circle, fill="grey")  # Turn off the red circle when the thread is stopped


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
        self.check_statut_client()
        if self.running and self.recording:
            transcriptions, phrase_finished =self.client.get_transcriptions()
            transcriptions = transcriptions if self.client else []
            corrected_transcriptions = [self.correcteur.applique_corrections(line) for line in transcriptions]
            combined_text = ' '.join(corrected_transcriptions)
            if combined_text != "":
                complet_transcriptions = self.current_mode.update_transcription(corrected_transcriptions)

                if self.simulate_keyboard:
                    self.animate_typing(combined_text)
                
                # if phrase_finished:
                self.last_transcription = complet_transcriptions
                #     self.start_client()
                # else:
            self.root.after(500, self.update_transcriptions)
            # else:
            #     self.root.after(500, self.update_transcriptions)
            
    def update_monitoring(self):
        if self.stream:
            self.current_mode.update_monitoring()
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

    def toggle_start_stop(self):
        """
        Toggle the start/stop state of the transcription client.
        """
        if self.running:
            self.stop_client()
        else:
            self.start_client()

    def hide_window(self):
        self.current_mode.hide_window()
        # self.simulate_keyboard_var.set(True)
        self.root.withdraw()
        self.is_hidden = True

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

    def switch_mode(self, mode):
            if self.current_mode:
                self.modes[self.current_mode].exit()
            self.current_mode = mode
            self.modes[mode].enter()

    def exit_program(self):
        """
        Exit the program gracefully, ensuring all resources are properly released.
        """
        # Stop the client if it is running
        if self.client:
            self.client.stop()
        if self.client_thread:
            self.client_thread.join()
            self.client_thread = None
        
        # Close the audio stream if it is open
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        
        # Terminate the PyAudio instance
        if hasattr(self, 'audio') and self.audio is not None:
            self.audio.terminate()

        # Close the PhilipsMic instance if it exists
        if hasattr(self, 'mic') and self.mic is not None:
            self.mic.disconnect()

        # Destroy the root window to close the Tkinter application
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = TranscriptionApp(root)
    # app.start_client()
    root.mainloop()
