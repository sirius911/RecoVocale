from tkinter import messagebox
import wave
from client import TranscriptionClient
from Correcteur import intercept, corrige_ponctuation
from utils_keyboard import Simulator
import threading
from info import APPRENTI
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
        self.ip_client = ip_client
        self.listen = listen

    def start_client(self, loop, port_service=None, audio_file=None, listen=False):
        port = port_service
        if port is None:
            port = self.port
        print(f"Starting client in ClientManager in [{port}]")
        self.stop_client()  # Ensure any previous client is stopped before starting a new one

        if self.client is None:
            self.client = TranscriptionClient(
                self.host,
                port,
                lang=self.lang,
                model=self.model,
                translate=self.translate,
                use_vad=self.use_vad,
                save_output_recording=self.save_output_recording,
                output_recording_filename=self.output_recording_filename,
                call_back=self.call_back,
                nb_repeat=self.nb_repeat,
                ip_client=self.ip_client,
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
            self.client(audio=self.audio_file, listen=self.listen)
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
            return False
        
        combined_text = texte.lstrip()

        if self.fenetre_gestion_insertions() or self.mode == APPRENTI:
            # pas d'interceptions
            pass
        else:
            combined_text = intercept(combined_text, self.insertions.get())

        if combined_text != "":
            if self.mode != APPRENTI:
                # En mode APPRENTI on ne mets pas les ponctuations écrites (point, virgule etc...)
                combined_text = corrige_ponctuation(combined_text)
            if not self.fenetre_gestion_insertions():
                # on appelle la fonction du mode qui permet soit d'écrire dans la TextBox soit d'envoyer la chaine écrite
                # on n'appelle la fonction que si le client n'est pas dans la fenêtre de gestion des insertions 
                self.update_callback(combined_text, ending)
            else:
                # la fenetre insertion est ouverte on va alors envoyer le texte sur l'écran
                if ending:
                   Simulator(combined_text) 
        return not ending # on renvoi la demande de recording du client donc l'inverse de ending à la fonction qui a appelé le call back

    def stop_client(self):
        if not self.running:
            return
        self.running = False
        if self.client:
            self.client.stop()
            self.client = None
        # NE PAS join() si on est dans le thread lui-même
        if self.client_thread is not None and threading.current_thread() != self.client_thread:
            self.client_thread.join()
        self.client_thread = None

    def pause(self):
        if self.client:
            self.client.set_pause(True)