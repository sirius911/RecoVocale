from client import EnhancedTranscriptionClient
from Correcteur import Correcteur, intercept
import threading
import asyncio
import traceback

class ClientManager:
    def __init__(self, host, port, lang, model, translate, use_vad, save_output_recording, output_recording_filename, update_callback):
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
        self.correcteur = Correcteur()

    def start_client(self, loop):
        print("Starting client in ClientManager")
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
        self.client.set_pause(False)
        self.running = True
        self.client
        self.loop = loop
        # Run the client in a separate thread to avoid blocking the event loop
        self.client_thread = threading.Thread(target=self.run_client_thread)
        self.client_thread.start()
        self.display_task = asyncio.run_coroutine_threadsafe(self.update_transcription(0), self.loop)

    def run_client_thread(self):
        try:
            self.client()
        except Exception as e:
            print(f"Error running client: {e}")

    async def update_transcription(self, compteur):
        ancienne_transcription = ""
        try:
            while self.running:
                
                transcriptions, _ = self.client.get_transcriptions()
                transcriptions = transcriptions if self.client else []
                # corrected_transcriptions = [self.correcteur.applique_corrections(line) for line in transcriptions]
                
                combined_text, ending = intercept(''.join(transcriptions).lstrip())
                
                if combined_text.lstrip() != '' and combined_text == ancienne_transcription and self.client.is_pause():
                    compteur += 1
                else:
                    ancienne_transcription = combined_text
                    compteur = 0

                # print(f"compteur = {compteur} et client.is_pause = {self.client.is_pause()}")
                ending = ending or (compteur > 1) # fin demandé par intercept() ou 2 fois le meme text en mode pause
                if combined_text != "":
                    self.update_callback(combined_text, ending)
                if ending:
                    print("Fin de transcription demandée")
                    self.stop_client()
                await asyncio.sleep(0.5)
        except Exception as e:
            print(e)
            traceback.print_exc()
        print("sortie du while")

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
        if self.display_task:
            self.display_task.cancel()
            self.display_task = None

    def pause(self):
        if self.client:
            self.client.set_pause(True)
