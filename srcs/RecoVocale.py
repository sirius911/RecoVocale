import tkinter as tk
import asyncio
import threading
import keyboard

import pyaudio
from GrandFenetreMode import GrandFenetreMode
from ReduitMode import ReduitMode
from utils_socket import check_server_status
from utils_keyboard import Simulator
from Micro import Micro
from info import *
from ClientManager import ClientManager

class App:
    def __init__(self, root, loop):
        print("Initializing App")
        self.root = root
        self.root.title(f"RecoVocale [{SERVEUR_IP}:{PORT}] (v{VERSION})")
        self.root.attributes("-topmost", True)  # Keep the window on top of others

        self.recording = False
        self.last_transcriptions = ""
        self.current_transcriptions = ""
    
        #-------------------check serveur-----------------------
        self.status_server = check_server_status(SERVEUR_IP, PORT)

        #-----------------Shortcut------------------------------
        self.keyboard_shortcut = SHORTCUT

        # -------------simulate keyboard
        self.simulate_keyboard = False
        self.simulator_keyboard = Simulator()
        keyboard.add_hotkey(self.keyboard_shortcut, self.toggle_start_stop)
        #----------------------MODE----------------------------
        self.current_mode = ReduitMode(self)
        #----------------- Lien Client Whisper -----------------------
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
        # Initialize the microphone 
        self.mic = Micro(loop, app=self)


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
            self.current_mode.update() 

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

    def switch_mode(self, mode):
        print(f"switch_mode({mode.name})")
        if self.current_mode:
            if self.current_mode.mode != mode:
                if mode == ModeStyle.BIG:
                    self.current_mode.exit()
                    self.current_mode = GrandFenetreMode(self)
                elif mode == ModeStyle.SMALL:
                    self.current_mode.exit()
                    self.current_mode = ReduitMode(self)
                else:
                    print("Erreur de Mode dans App")
                self.current_mode.update()


def start_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

# def on_resize(event):
#         # Afficher les dimensions de la fenêtre dans la barre de titre
#         width = event.width
#         height = event.height
#         print(f"Ma fenêtre Tkinter - Dimensions: {width}x{height}")

if __name__ == "__main__":
    root = tk.Tk()
    root.resizable(False, False)
    # Create a new event loop
    new_loop = asyncio.new_event_loop()
    threading.Thread(target=start_loop, args=(new_loop,), daemon=True).start()

    app = App(root, new_loop)  # Pass the new loop to the app
    # root.bind("<Configure>", on_resize)
    root.mainloop()
