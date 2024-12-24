import time
import tkinter as tk
from tkinter import messagebox
import threading
import pyaudio
import numpy as np
import asyncio  # Import asyncio
from client import EnhancedTranscriptionClient
from Correcteur import Correcteur
import socket
from pynput.keyboard import Controller, Key
import ctypes  # Import ctypes to interact with the Windows API
import keyboard
from pystray import MenuItem as item
from PIL import Image, ImageDraw
from PhilipsMic import PhilipsMic  # Import the PhilipsMic class
from GrandFenetreMode import GrandFenetreMode

SERVEUR_IP = "10.1.11.215"
PORT = 9090
VERSION = "0.5"
SHORTCUT = "F3"

class TranscriptionApp:
    def __init__(self, root):
        self.root = root
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
        self.transcription_task = None
        self.running = False
        self.recording = False
        self.status_server = False
        self.previous_text = "" # using in simulate keyboard
        self.last_transcription = ""

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
        
        # Register global hotkeys
        keyboard.add_hotkey(self.keyboard_shortcut, self.toggle_start_stop)

        # Initialize PhilipsMic
        self.mic = PhilipsMic(self.start_client, self.pause, self.stop_client)

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

    def minimize_console(self):
        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32
        hWnd = kernel32.GetConsoleWindow()
        if hWnd:
            user32.ShowWindow(hWnd, 6)  # SW_MINIMIZE = 6

    def check_server_status(self):
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

    def start_client(self):
        if not self.status_server or not self.check_micro:
            return
        if not self.running:
            self.client = self.create_client()
            self.running = True
            asyncio.create_task(self.client())
            self.previous_text = ""
        else:
            self.client.set_pause(False)
            self.recording = True

        if not self.transcription_task:
            self.transcription_task = asyncio.create_task(self.update_transcriptions())

    def pause(self):
        if self.running and self.client is not None:
            self.recording = False
            self.client.set_pause(True)

    def stop_client(self):
        self.running = False
        if self.transcription_task:
            self.transcription_task.cancel()
            self.transcription_task = None
        if self.client:
            self.client.stop()

    async def update_transcriptions(self):
        while self.running:
            transcriptions, phrase_finished = self.client.get_transcriptions()
            transcriptions = transcriptions if self.client else []
            corrected_transcriptions = [self.correcteur.applique_corrections(line) for line in transcriptions]
            combined_text = ' '.join(corrected_transcriptions)
            if combined_text != "":
                complet_transcriptions = self.current_mode.update_transcription(corrected_transcriptions)
                if self.simulate_keyboard:
                    self.animate_typing(combined_text)
            await asyncio.sleep(0.5)

    async def async_main(self):
        while True:
            await asyncio.sleep(0.1)
            self.root.update()

    def start_async_loop(self):
        asyncio.run(self.async_main())

    def update_monitoring(self):
        if self.stream:
            self.current_mode.update_monitoring()
        self.root.after(100, self.update_monitoring)

    def animate_typing(self, new_text:str):
        def find_common_prefix(s1, s2):
            common_prefix_length = 0
            for c1, c2 in zip(s1, s2):
                if c1 != c2:
                    break
                common_prefix_length += 1
            return common_prefix_length
        
        common_prefix_length = find_common_prefix(self.previous_text, new_text)
        for _ in range(len(self.previous_text) - common_prefix_length):
            self.keyboard.press(Key.backspace)
            self.keyboard.release(Key.backspace)
            time.sleep(0.02)

        new_part = new_text[common_prefix_length:]
        for char in new_part:
            self.type_character(char)
            time.sleep(0.02)  # Add a small delay to simulate typing speed
        
        self.previous_text = new_text

    def type_character(self, char:str):
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
        if self.running:
            self.stop_client()
        else:
            self.start_client()

    def hide_window(self):
        self.current_mode.hide_window()
        self.simulate_keyboard = True
        self.root.withdraw()
        self.is_hidden = True
    
    def change_shortcut(self):
        self.root.attributes("-topmost", False)
        self.shortcut_window = tk.Toplevel(self.root)
        self.shortcut_window.title("Changer le raccourci clavier")
        self.shortcut_window.attributes("-topmost", True)

        tk.Label(self.shortcut_window, text="Appuyez sur une nouvelle combinaison de touches :").pack(pady=10)
        self.shortcut_entry = tk.Entry(self.shortcut_window)
        self.shortcut_entry.pack(pady=10)
        self.shortcut_entry.bind('<KeyPress>', self.get_shortcut)
        self.shortcut_entry.focus_set()

        self.keyboard_shortcut = ''
        self.shortcut_entry.delete(0, tk.END)

        self.shortcut_window.protocol("WM_DELETE_WINDOW", self.on_close_shortcut_window)

    def on_close_shortcut_window(self):
        self.root.attributes("-topmost", True)
        self.shortcut_window.destroy()

    def get_shortcut(self, event):
        key = self.map_key_name(event.keysym)

        if key == 'Return':
            if self.is_valid_shortcut(self.keyboard_shortcut.split('+')):
                keyboard.clear_all_hotkeys()
                keyboard.add_hotkey(self.keyboard_shortcut, self.toggle_start_stop)
                self.start_button.config(text=f"Start ({self.keyboard_shortcut})")
                self.stop_button.config(text=f"Stop ({self.keyboard_shortcut})")
                self.icon.title = f"RecoVocale (v{VERSION})[{self.keyboard_shortcut}]"
                self.on_close_shortcut_window()
            else:
                messagebox.showerror("Raccourci invalide", "La combinaison de touches n'est pas valide.")
                self.keyboard_shortcut = ''
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
            return True
        if len(keys) == 2 and 'ctrl' in keys:
            return True
        if len(keys) == 3 and 'ctrl' in keys and 'shift' in keys:
            return True
        if len(keys) == 3 and 'ctrl' in keys and 'alt' in keys:
            return True
        if len(keys) == 4 and 'ctrl' in keys and 'alt' in keys and 'shift' in keys:
            return True
        return False

    def map_key_name(self, key):
        key_mapping = {
            'Control_L': 'ctrl',
            'Control_R': 'ctrl',
            'Shift_L': 'shift',
            'Shift_R': 'shift',
            'Alt_L': 'alt',
            'Alt_R': 'alt'
        }
        return key_mapping.get(key, key)

    def switch_mode(self, mode):
        if self.current_mode:
            self.modes[self.current_mode].exit()
        self.current_mode = mode
        self.modes[mode].enter()

    def exit_program(self):
        self.running = False
        if self.transcription_task:
            self.transcription_task.cancel()
            self.transcription_task = None

        if self.client:
            self.client.stop()
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        
        if hasattr(self, 'audio') and self.audio is not None:
            self.audio.terminate()

        if hasattr(self, 'mic') and self.mic is not None:
            self.mic.disconnect()

        self.root.quit()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = TranscriptionApp(root)
    asyncio.run(app.start_async_loop())
    root.mainloop()
