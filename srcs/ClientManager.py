from client import TranscriptionClient
from Correcteur import intercept, corrige_ponctuation
from utils_keyboard import Simulator
import threading
from info import APPRENTI

class ClientManager:
    def __init__(self, host, port, lang, model, translate, use_vad, save_output_recording, output_recording_filename, update_callback, insertions, fenetre_gestion_insertions, mode, nb_repeat=2):
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
        # self.display_task = None
        self.loop = None
        self.update_callback = update_callback
        self.insertions = insertions
        self.fenetre_gestion_insertions = fenetre_gestion_insertions
        # self.ancienne_transcription = ""
        self.mode = mode
        self.nb_repeat = nb_repeat # nb de fois que la transcription doit etre répété pour demander un fin de transcription

    def start_client(self, loop):
        print("Starting client in ClientManager")
        self.stop_client()  # Ensure any previous client is stopped before starting a new one

        if self.client is None:
            self.client = TranscriptionClient(
                self.host,
                self.port,
                lang=self.lang,
                model=self.model,
                translate=self.translate,
                use_vad=self.use_vad,
                save_output_recording=self.save_output_recording,
                output_recording_filename=self.output_recording_filename,
                call_back=self.call_back,
                nb_repeat=self.nb_repeat,
            )
        self.client.set_pause(False)
        self.running = True
        self.loop = loop
        # self.compteur = 0
        # self.ancienne_transcription = ""
        # Run the client in a separate thread to avoid blocking the event loop
        self.client_thread = threading.Thread(target=self.run_client_thread)
        self.client_thread.start()

    def run_client_thread(self):
        try:
            self.client()
            self.client = None
        except Exception as e:
            print(f"Error running client: {e}")

    def call_back(self, texte, ending):
        # Fonction appelé par Client.py suite a evenement websocket serveur WhisperLive
        if texte is None:
            self.update_callback(None, True)
            return
        transcriptions = texte if self.client else []
        if self.fenetre_gestion_insertions() or self.mode == APPRENTI:
            # la fenetre des insertions est ouverte donc on n'intercepte pas 
            combined_text = ''.join(transcriptions).lstrip()
            # ending = False
        else:
            combined_text, stop = intercept(''.join(transcriptions).lstrip(), self.insertions.get())
            ending = ending or stop
        # if combined_text.lstrip() != '' and combined_text == self.ancienne_transcription and self.client.is_pause():
        #     self.compteur += 1
        # else:
        #     self.ancienne_transcription = combined_text
        #     self.compteur = 0
        # ending = ending or (self.compteur >= self.nb_repeat) # fin demandé par intercept() ou nb_repeat fois le meme text en mode pause
        if combined_text != "":
            if self.mode != APPRENTI:
                combined_text = corrige_ponctuation(combined_text)
            if not self.fenetre_gestion_insertions():
                # on appelle la fonction du mode
                self.update_callback(combined_text, ending)
            else:
                # la fenetre insertion est ouverte
                if ending:
                   Simulator(combined_text) 
        return not ending # on renvoi la demande de recording du client donc l'inverse de ending
            # if ending:
            #         print("Fin de transcription demandée")
            #         if self.fenetre_gestion_insertions():
            #             Simulator(combined_text)
            #         self.running = False
                    # return False # recording = False
        # return True

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
