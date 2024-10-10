import asyncio
import numpy as np
import threading
import sounddevice as sd
# from scipy.io.wavfile import write
from Mode import Mode
from utils_window import create_menus, create_buttons
from info import RECORD
import tkinter as tk

class AudioManager:
    def __init__(self):
        self.fs = 16000  # Taux d'échantillonnage
        self.channels = 1  # Mono
        self.dtype = 'float32'  # 32 bits flottants
        self.audio_data = []
        self.is_recording = False
        self.is_paused = False
        self.recording_task = None
        self.loop = None

    def start_recording(self, loop):
        self.stop_recording()  # Assurez-vous que tout enregistrement précédent est arrêté

        self.is_recording = True
        self.is_paused = False
        self.audio_data = []
        self.loop = loop

        # Lancer l'enregistrement dans un thread séparé
        self.recording_task = threading.Thread(target=self._record_audio_thread)
        self.recording_task.start()

    def _record_audio_thread(self):
        def callback(indata, frames, time, status):
            if self.is_recording and not self.is_paused:
                self.audio_data.append(indata.copy())

        with sd.InputStream(samplerate=self.fs, channels=self.channels, dtype=self.dtype, callback=callback):
            while self.is_recording:
                sd.sleep(100)

    def stop_recording(self):
        if not self.is_recording:
            return

        self.is_recording = False
        if self.recording_task:
            self.recording_task.join()
            self.recording_task = None

        # Sauvegarder les données audio
        if self.audio_data:
            audio_array = np.concatenate(self.audio_data, axis=0)
            # write('enregistrement.wav', self.fs, audio_array)
            print("Enregistrement sauvegardé en tant que 'enregistrement.wav'")

    def pause_recording(self):
        if self.is_recording:
            self.is_paused = True

    def unpause_recording(self):
        if self.is_recording:
            self.is_paused = False



class Mode_Record(Mode):
    def enter(self):
        self.mode = RECORD
        # self.app.simulate_keyboard = RECORD.simule_keyboard
        self.mod_var.set(RECORD)
        self.ui()
        self.client_manager = None
        self.audio_manager = AudioManager()
        super().enter()

    def ui(self):
        create_menus(self)
        create_buttons(self)

        self.valide_button = tk.Button(self.root, text=f"Sauvegarde", command=self.sauvegarde)
        self.valide_button.pack(side=tk.RIGHT,pady=10)
        # self.app.status_label = tk.Label(self.root, text="Server status: Unknown", fg="blue")
        # self.app.status_label.pack(pady=10)

    def start(self):
        print("START IN RECORD Mode... Nothing to do")

    def sauvegarde(self):
        self.audio_manager.start_recording(self.app.loop)

    def stop(self):
        print("Enregistrement arrêté")
        self.audio_manager.stop_recording()

    def unpause(self):
        if not self.audio_manager.is_recording:
            print("Enregistrement démarré")
            asyncio.run_coroutine_threadsafe(self.start_audio_recording(), self.app.loop)
        elif self.audio_manager.is_paused:
            print("Reprise de l'enregistrement")
            self.audio_manager.unpause_recording()

    def pause(self):
        if self.audio_manager.is_recording:
            print("Enregistrement en pause")
            self.audio_manager.pause_recording()

    def copy_to_clipboard(self):
        pass

    async def start_audio_recording(self):
        self.audio_manager.start_recording(self.app.loop)

    def valid_transcriptions(self):
        pass

    def update_transcription(self, message):
        pass


