import os
from client import TranscriptionClient
from Correcteur import intercept, corrige_ponctuation
from utils_keyboard import Simulator
import threading
from info import APPRENTI

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
        self.mode = mode
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
            print(f"Error running client: {e}")

    def call_back(self, texte, ending):
        # Fonction appelé par Client.py suite a evenement websocket serveur WhisperLive
        if texte is None: # appel du call back suite à ending=True
            return False
        transcriptions = texte if self.client else []
        if self.fenetre_gestion_insertions() or self.mode == APPRENTI:
            # la fenetre des insertions est ouverte donc on n'intercepte pas 
            combined_text = ''.join(transcriptions).lstrip()
        else:
            #On passe transcriptions a intercept() pour les insertions automatiques date, chiffre romain etc...
            combined_text = intercept(''.join(transcriptions).lstrip(), self.insertions.get())

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
        if self.client_thread:
            self.client_thread.join()
            self.client_thread = None

    def pause(self):
        if self.client:
            self.client.set_pause(True)