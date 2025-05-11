from tkinter import messagebox
import wave
from client import Client
from Correcteur import intercept, corrige_ponctuation
from utils_keyboard import Simulator
import threading
from info import APPRENTI, REDUIT
import traceback

class ClientManager:
    def __init__(self, host, port, lang, model, translate, use_vad, save_output_recording, output_recording_filename, update_callback, insertions, fenetre_gestion_insertions, mode, nb_repeat=2, ip_client="0.0.0.0", listen=False):
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
        self.loop = None
        self.update_callback = update_callback
        self.insertions = insertions
        self.fenetre_gestion_insertions = fenetre_gestion_insertions
        self.mode = mode.mode # Direct, Reduit etc...
        self._mode = mode
        self.nb_repeat = nb_repeat # nb de fois que la transcription doit etre répété pour demander un fin de transcription
        self.last_partial_text = ""
        self.ip_client = ip_client
        self.listen = listen

    def start_client(self, loop, port_service=None, audio_file=None, listen=False):
        port = port_service
        if port is None:
            port = self.port
        print(f"Starting client in ClientManager in [{port}]")
        self.stop_client()  # Ensure any previous client is stopped before starting a new one

        self.client = Client(
            host=self.host,
            port=port,
            lang=self.lang,
            model=self.model,
            translate=self.translate,
            use_vad=self.use_vad,
            save_output_recording=self.save_output_recording,
            output_recording_filename=self.output_recording_filename,
            call_back=self.call_back,
            nb_repeat=self.nb_repeat,
            ip_client=self.ip_client
        )
        self.audio_file = audio_file
        self.listen = listen
        self.client.set_pause(False)
        self.running = True
        self.loop = loop
        # Run the client in a separate thread to avoid blocking the event loop
        self.client_thread = threading.Thread(target=self.run_client_thread)
        self.client_thread.start()

    def run_client_thread(self):
        try:
            # ⏳ Attente active de la WebSocket READY
            if not self.client.ready_event.wait(timeout=5):  # max 5 secondes
                print("[ERROR] Le serveur n'a pas répondu à temps.")
                self.stop_client()
                self._mode.stop_client()
                return

            if self.audio_file:
                self.client.source_is_micro = False
                self.client.play_file(self.audio_file, listen=self.listen)
            else:
                self.client.source_is_micro = True
                self.client.record()

            self.client = None
        except Exception as e:
            print("Traceback complet :")
            traceback.print_exc()

            if isinstance(e, (EOFError, wave.Error)):
                messagebox.showerror(
                    "Fichier audio invalide",
                    f"Le fichier ne peut pas être lu comme un fichier audio valide.\n\n"
                    f"Fichier :\n{self.audio_file}\n\nErreur :\n{e}"
                )
            else:
                print(f"Erreur dans run_client :{repr(e)}")
                      
            self.stop_client()
            self._mode.stop_client() # on stop le client appelant

    def call_back(self, texte, ending, force=False):
        # Fonction appelé par Client.py suite a evenement websocket serveur WhisperLive
        # print(f"[DEBUG] call_back('{texte}', {ending}, {force})")
        if texte is None: # appel du call back suite à ending=True
            # print(f"*************ici self._mode.app.recording = {self._mode.app.recording}")
            if self.audio_file is not None or force:
                self._mode.app.recording = False
                self.update_callback(None, True)
            return
        
        # if self.mode == REDUIT and self.client:
        #     combined_text = (
        #         self.client.get_transcription_complete().lstrip()
        #         if ending else texte.lstrip()
        #     )
        # else:
        combined_text = texte.lstrip()

        if not (self.fenetre_gestion_insertions() or self.mode == APPRENTI):
            combined_text = intercept(combined_text, self.insertions.get())
            if self.mode != APPRENTI:
                combined_text = corrige_ponctuation(combined_text)

        if combined_text != "":
            # if self.mode == REDUIT and not ending:
            #     if not hasattr(self, "last_partial_text"):
            #         self.last_partial_text = ""
            #         self.repeat_counter = 0

            #     if combined_text == self.last_partial_text:
            #         # ✅ Si phrase stable ET ponctuée, ou répétée assez souvent
            #         if combined_text.endswith(('.', '!', '?')) or self.repeat_counter >= self.nb_repeat:
            #             self.repeat_counter += 1
            #             if self.repeat_counter >= self.nb_repeat:
            #                 print(f"[REPEAT] Texte stable détecté : {texte} (compteur = {self.repeat_counter})")
            #                 ending = True
            #                 print("[VALIDATION] Texte validé par répétition")

            #         else:
            #             self.repeat_counter += 1
            #     else:
            #         self.last_partial_text = combined_text
            #         self.repeat_counter = 1
            # elif self.mode != REDUIT:
            #     # Réinitialiser pour les autres modes
            #     self.last_partial_text = ""
            #     self.repeat_counter = 0

            if not self.fenetre_gestion_insertions():
                self.update_callback(combined_text, ending)
            else:
                if ending:
                    Simulator(combined_text)

    def stop_client(self):
        self.running = False

        # Stopper le client WebSocket proprement
        if self.client:
            try:
                self.client.stop()
            except Exception as e:
                print(f"[ERROR] lors de l'arrêt du client : {e}")
            self.client = None

        # Attendre la fin du thread si on n'est pas déjà dedans
        if self.client_thread is not None:
            if threading.current_thread() != self.client_thread:
                self.client_thread.join()
            self.client_thread = None

    def pause(self):
        if self.client:
            self.client.set_pause(True)