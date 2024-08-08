import tkinter as tk
from tkinter import scrolledtext
import asyncio
import threading
import keyboard

import pyaudio
from client import EnhancedTranscriptionClient
from GrandFenetreMode import GrandFenetreMode
from utils_socket import check_server_status
from utils_keyboard import Simulator
from Correcteur import Correcteur
from PhilipsMic import PhilipsMic  # Import the PhilipsMic class

SERVEUR_IP = "10.1.11.215"
PORT = 9090
VERSION = "0.5"
SHORTCUT = "F3"

class ClientManager:
    def __init__(self, host, port, lang, model, translate, use_vad, save_output_recording, output_recording_filename, update_callback):
        # print("Initializing ClientManager")
        self.host = host
        self.port = port
        self.lang = lang
        self.model = model
        self.translate = translate
        self.use_vad = use_vad
        self.save_output_recording = save_output_recording
        self.output_recording_filename = output_recording_filename
        self.client = None
        self.running = False
        self.client_thread = None
        self.display_task = None
        self.loop = None
        self.update_callback = update_callback
        self.correcteur = Correcteur("../dist/corrections.json")

    def start_client(self, loop):
        # print("Starting client in ClientManager")
        self.stop_client()  # Ensure any previous client is stopped before starting a new one

        if self.client is None:
            self.client = EnhancedTranscriptionClient(
                self.host,
                self.port,
                lang=self.lang,
                model=self.model,
                translate=self.translate,
                use_vad=self.use_vad,
                save_output_recording=self.save_output_recording,
                output_recording_filename=self.output_recording_filename
            )

        self.running = True
        # print(f"Starting client, running: {self.running}")

        self.loop = loop
        # Run the client in a separate thread to avoid blocking the event loop
        self.client_thread = threading.Thread(target=self.run_client_thread)
        self.client_thread.start()

        # print("Creating display task")
        self.display_task = asyncio.run_coroutine_threadsafe(self.update_display(), self.loop)
        # print("Display task started:", self.display_task)

    def run_client_thread(self):
        try:
            # print("run_client()")
            self.client()
            # print("Client started")
        except Exception as e:
            print(f"Error running client: {e}")

    async def update_display(self):
        # print("update_display started")
        while self.running:
            # print("update_display running")
            transcriptions, phrase_finished = self.client.get_transcriptions()
            transcriptions = transcriptions if self.client else []
            corrected_transcriptions = [self.correcteur.applique_corrections(line) for line in transcriptions]
            # corrected_transcriptions = [line for line in transcriptions]
            combined_text = ' '.join(corrected_transcriptions)
            if combined_text != "":
                # print("update_callback called with:", combined_text)
                self.update_callback(combined_text)
            # else:
                # print("combined_text in ClientManager.update_display() -> empty")
            await asyncio.sleep(0.5)

    def stop_client(self):
        if not self.running:
            return

        self.running = False
        print("Stopping client")
        if self.client:
            self.client.stop()
            self.client = None
        if self.client_thread:
            self.client_thread.join()
            self.client_thread = None
        if self.display_task:
            self.display_task.cancel()
            self.display_task = None

    def pause(self):
        print("pause client")
        if self.client:
            self.client.set_pause(True)

    def unpause(self):
        print("record")
        if self.client:
            self.client.set_pause(False)

class App:
    def __init__(self, root, loop):
        print("Initializing App")
        self.root = root
        self.root.title(f"RecoVocale [{SERVEUR_IP}:{PORT}] (v{VERSION})")
        self.root.attributes("-topmost", True)  # Keep the window on top of others

        self.recording = False
        self.last_transcriptions = ""
        self.current_transcriptions = ""

        #--------------- check micro -----------------
        try:
            self.audio = pyaudio.PyAudio()
            self.selected_micro = self.audio.get_default_input_device_info()["index"]
            self.check_micro = True
        except OSError:
            print("Pas de micro ...")
            self.selected_micro = None
            self.check_micro = False
    
        #-------------------check serveur-----------------------
        self.status_server = check_server_status(SERVEUR_IP, PORT)

        #-----------------Shortcut------------------------------
        self.keyboard_shortcut = SHORTCUT

        # -------------simulate keyboard
        self.simulate_keyboard = False
        self.simulator_keyboard = Simulator()
        keyboard.add_hotkey(self.keyboard_shortcut, self.toggle_start_stop)
        #----------------------MODE----------------------------
        self.current_mode = GrandFenetreMode(self)

        self.client_manager = ClientManager(
            SERVEUR_IP,
            PORT,
            "fr",
            "small",
            False,
            True,
            False,
            "",
            self.display_message  # Pass the callback to ClientManager
        )

        # Use the provided asyncio event loop
        self.loop = loop

        self.root.protocol("WM_DELETE_WINDOW", self.current_mode.exit_app)

        # Start the client automatically on launch
        self.start_client()

        # #---------------------------MICRO----------------------------
        # Initialize PhilipsMic with the asyncio loop
        self.mic = PhilipsMic(loop, on_no_touch=self.pause,
                              on_rec_push=self.unpause,
                              on_play_push=self.valid_transcriptions,
                              on_f1_push=None)


    def start_client(self):
        # print("Starting client in App")
        self.client_manager.start_client(self.loop)
        self.pause()  # In pause 

    def stop_client(self):
        # print("Stopping client in App")
        self.client_manager.stop_client()
        self.recording = False
        self.update()

    def valid_transcriptions(self):
        # on valide les transcription et sauvegarde
        self.current_transcriptions += '\n'
        self.last_transcriptions += self.current_transcriptions
        if self.simulate_keyboard:
            self.simulator_keyboard.animate_typing(self.current_transcriptions)
            self.simulator_keyboard.init()
        self.current_transcriptions = ""
        self.stop_client()
        self.start_client()

    def pause(self):
        print("Pausing client in App")
        self.client_manager.pause()
        self.recording = False
        self.current_transcriptions += '\n' 
        self.update()

    def unpause(self):
        # print("Unpausing client in App")
        if not self.recording:
            self.client_manager.unpause()
            self.recording = True
            self.update()

    def running(self):
        return self.client_manager.running

    def display_message(self, message):
        self.current_transcriptions = message
        self.current_mode.update_transcription(message)
        if self.simulate_keyboard and self.recording:
            self.simulator_keyboard.animate_typing(message)

    def update(self):
        if self.current_mode:
            self.current_mode.update_rec_circle()
            self.current_mode.update_image_button()    

    def on_closing(self):
        self.stop_client()
        self.root.quit()
        self.loop.stop()

    def toggle_start_stop(self):
        """
        Toggle the start/stop state of the transcription client.
        """
        if self.recording:
            self.pause()
        else:
            self.unpause()

def start_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

if __name__ == "__main__":
    root = tk.Tk()

    # Create a new event loop
    new_loop = asyncio.new_event_loop()
    threading.Thread(target=start_loop, args=(new_loop,), daemon=True).start()

    app = App(root, new_loop)  # Pass the new loop to the app
    root.mainloop()
