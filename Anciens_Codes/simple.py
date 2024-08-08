import tkinter as tk
from tkinter import scrolledtext
import asyncio
import threading
from client import EnhancedTranscriptionClient

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

    def start_client(self, loop):
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
        print(f"Starting client, running: {self.running}")

        self.loop = loop
        # Run the client in a separate thread to avoid blocking the event loop
        self.client_thread = threading.Thread(target=self.run_client_thread)
        self.client_thread.start()

        self.display_task = asyncio.run_coroutine_threadsafe(self.update_display(), self.loop)

    def run_client_thread(self):
        try:
            print("run_client()")
            self.client()
            print("Client started")
        except Exception as e:
            print(f"Error running client: {e}")

    async def update_display(self):
        while self.running:
            print("ici")
            transcriptions, phrase_finished = self.client.get_transcriptions()
            transcriptions = transcriptions if self.client else []
            corrected_transcriptions = [line for line in transcriptions]  # Simplified for now
            combined_text = ' '.join(corrected_transcriptions)
            if combined_text != "":
                self.update_callback(combined_text)  # Call the callback to update the UI
            await asyncio.sleep(0.5)  # Update every 500ms

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

#### `App` utilisant le Callback

class App:
    def __init__(self, root, loop):
        self.root = root
        self.root.title("Async Tkinter Example")

        self.text_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=40, height=10)
        self.text_area.pack(pady=20)

        self.connect_button = tk.Button(root, text="Connect", command=self.start_client)
        self.connect_button.pack(pady=10)

        self.stop_button = tk.Button(root, text="Stop Client", command=self.stop_client)
        self.stop_button.pack(pady=10)

        self.pause_button = tk.Button(root, text="Pause", command=self.pause)
        self.pause_button.pack(pady=10)

        self.unpause_button = tk.Button(root, text="UnPause", command=self.unpause)
        self.unpause_button.pack(pady=10)

        self.host = "10.1.11.215"
        self.port = 9090
        self.lang = "fr"
        self.model = "small"
        self.translate = False
        self.use_vad = True
        self.save_output_recording = False
        self.output_recording_filename = "./output_recording.wav"

        self.client_manager = ClientManager(
            self.host,
            self.port,
            self.lang,
            self.model,
            self.translate,
            self.use_vad,
            self.save_output_recording,
            self.output_recording_filename,
            self.display_message  # Pass the callback to ClientManager
        )

        # Use the provided asyncio event loop
        self.loop = loop
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Start the client automatically on launch
        self.start_client()

    def start_client(self):
        self.client_manager.start_client(self.loop)
        self.pause()

    def stop_client(self):
        self.client_manager.stop_client()

    def pause(self):
        self.client_manager.pause()

    def unpause(self):
        self.client_manager.unpause()

    def display_message(self, message):
        self.text_area.delete('1.0', tk.END)
        self.text_area.insert(tk.END, message + '\n')
        self.text_area.see(tk.END)

    def on_closing(self):
        self.stop_client()
        self.root.quit()
        self.loop.stop()

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
