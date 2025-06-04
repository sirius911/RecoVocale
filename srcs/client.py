
import os
import shutil
import struct
import wave
import numpy as np
import pyaudio
import threading
import json
import websocket
import uuid
import time
import tempfile
from typing import Any

TEMP_DIR = tempfile.gettempdir()


class Client:
    """
    Client WebSocket pour la transmission audio en temps réel à un serveur de transcription.

    Gère la capture micro, l'envoi des paquets, la lecture de fichiers audio,
    la gestion de pause, les erreurs serveur, et l'enregistrement des segments reçus.
    """

    END_OF_AUDIO = "END_OF_AUDIO"

    def __init__(self, host, port, lang=None, translate=False, model=None, srt_file_path="output.srt",
                 use_vad=True, call_back=None, nb_repeat=3, ip_client="0.0.0.0",
                 save_output_recording=False, output_recording_filename="./output_recording.wav") -> None:
        """
        Initialise une instance de Client.

        Args:
            host (str): Adresse du serveur.
            port (int): Port WebSocket du serveur.
            lang (str, optional): Langue de transcription.
            translate (bool): Active la traduction si True.
            model (str, optional): Nom du modèle à utiliser.
            srt_file_path (str): Chemin du fichier SRT de sortie.
            use_vad (bool): Active la détection vocale (VAD).
            call_back (callable, optional): Fonction de rappel lors de la réception d'un segment.
            nb_repeat (int): Nombre de fois qu'un segment doit être confirmé.
            ip_client (str): IP du client pour le suivi.
            save_output_recording (bool): Active l'enregistrement complet.
            output_recording_filename (str): Fichier final de l'enregistrement.
        """
        self.recording = False
        self.pause = False
        self.task = "translate" if translate else "transcribe"
        self.uid = str(uuid.uuid4())
        self.waiting = False
        self.last_response_received = None
        self.disconnect_if_no_response_for = 15
        self.language = lang
        self.model = model
        self.model_path = ""
        self.server_error = False
        self.srt_file_path = srt_file_path
        self.use_vad = use_vad
        self.last_segment = None
        self.last_received_segment = None
        self.phrase_finished = False
        self.segments_valides = set()
        self.nb_repeat = nb_repeat
        self.ancienne_transcription = ''
        self.call_back = call_back
        self.ip_client = ip_client
        self.compteur = 0
        self.source_is_micro = True
        self.segments_buffer = {}  # clé = (start, end), valeur = texte

        self.chunk = 4096
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.record_seconds = 60000
        self.save_output_recording = save_output_recording
        self.output_recording_filename = output_recording_filename
        self.frames = b""
        self.p = pyaudio.PyAudio()
        self.chunk_dir = os.path.join(TEMP_DIR, "chunks")
        if self.save_output_recording:
            if os.path.exists(self.chunk_dir):
                shutil.rmtree(self.chunk_dir)
            os.makedirs(self.chunk_dir)

        self.transcript = []

        socket_url = f"ws://{host}:{port}"
        self.client_socket = websocket.WebSocketApp(
            socket_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )
        self.ws_thread = threading.Thread(target=self.client_socket.run_forever)
        self.ws_thread.daemon = True
        self.ws_thread.start()

        self.ready_event = threading.Event()

    def on_open(self, ws: websocket.WebSocketApp) -> None:
        """
        Méthode appelée lors de l'ouverture de la connexion WebSocket.
        Envoie les paramètres de session (langue, modèle, etc.) au serveur.

        Args:
            ws: Instance de la connexion WebSocket.
        """
        ws.send(json.dumps({
            "uid": self.uid,
            "language": self.language,
            "task": self.task,
            "model": self.model,
            "use_vad": self.use_vad,
            "ip_client": self.ip_client,
            "beam_size": 5,
            "best_of": 1,
            "patience": 0.5,
            "length_penalty": 1.0,
            "repetition_penalty": 1.5,
            "no_repeat_ngram_size": 3,
            "log_prob_threshold": -1.0,  # -0.5
            "no_speech_threshold": 0.3,  # 0.5
            "compression_ratio_threshold": 1.2,  # 1.5
            "condition_on_previous_text": False,
            "temperature": [0.2, 0.4],
            "initial_prompt": "Rapport médical"
        }))

    def on_message(self, ws: websocket.WebSocketApp, message: str) -> None:
        """
        Méthode appelée à la réception d'un message WebSocket.

        Args:
            ws (websocket.WebSocketApp): WebSocket utilisée.
            message (str): Message JSON reçu du serveur.
        """
        message = json.loads(message)
        if self.uid != message.get("uid"):
            return
        if "status" in message:
            if message["status"] == "WAIT":
                self.waiting = True
                print(f"Server full. Wait time: {round(message['message'])} min.")
            elif message["status"] == "ERROR":
                print(f"Server error: {message['message']}")
                self.server_error = True
            elif message["status"] == "WARNING":
                print(f"Server warning: {message['message']}")
            return
        if message.get("message") == "DISCONNECT":
            self.recording = False
        if message.get("message") == "SERVER_READY":
            self.last_response_received = time.time()
            self.recording = True
            self.server_backend = message["backend"]
            self.model_path = message.get("model", "")
            self.ready_event.set()  # ✅ Indiquer que le client est prêt
            return
        if "language" in message:
            self.language = message.get("language")
            return
        if "segments" in message:
            self.process_segments(message["segments"])

    def process_segments(self, segments: list[dict]) -> None:
        """
        Traite les segments de texte reçus du serveur, en appelant le callback
        avec ending=True si le segment est marqué comme terminé.

        Args:
            segments (list[dict]): Liste de segments contenant au minimum les clés "start",
            "end", "text" et "completed".
        """

        # print(f"Segments received: {segments}")
        for seg in segments:
            start = float(seg.get("start", 0))
            end = float(seg.get("end", 0))
            text = seg.get("text", "").strip()
            completed = seg.get("completed", False)

            # 🧠 Mise à jour du tampon segmenté
            self.segments_buffer[(start, end)] = text

            if not text:
                continue  # ⛔️ ignorer les segments vides

            if completed:
                if text not in self.segments_valides:
                    print("** SEGMENT COMPLETED **")
                    self.call_back(text, ending=True)
                    self.segments_valides.add(text)
            else:
                self.call_back(text, ending=False)
        self.last_response_received = time.time()

    def send_packet_to_server(self, message: bytes) -> None:
        """
        Envoie un paquet binaire (audio) au serveur via WebSocket.

        Args:
            message (bytes): Le message audio encodé à envoyer.
        """
        try:
            self.client_socket.send(message, websocket.ABNF.OPCODE_BINARY)
        except Exception as e:
            print(e)

    def close_websocket(self) -> None:
        """
        Ferme proprement la connexion WebSocket avec un code de fermeture et un message.
        """
        try:
            if self.client_socket and self.client_socket.sock and self.client_socket.sock.connected:
                code = 1000
                reason = self.ip_client
                close_payload = struct.pack("!H", code) + reason.encode("utf-8")
                self.client_socket.send(close_payload, websocket.ABNF.OPCODE_CLOSE)
                self.client_socket.close()
        except Exception as e:
            print(f"[ERROR] WebSocket close error: {e}")
        finally:
            self.client_socket = None  # ← éviter toute réutilisation future

    def wait_before_disconnect(self) -> None:
        """
        Attend que le temps limite sans réponse serveur soit écoulé avant de se déconnecter.
        """
        assert self.last_response_received
        while time.time() - self.last_response_received < self.disconnect_if_no_response_for:
            continue

    def stop(self) -> None:
        """
        Arrête l'enregistrement et ferme la connexion WebSocket.
        """
        self.close_websocket()
        self.recording = False
        self.client_socket = None  # ← CRUCIAL

    def is_recording(self) -> bool:
        """
        Indique si l'enregistrement est en cours.

        Returns:
            bool: True si enregistrement actif, sinon False.
        """
        return self.recording

    def set_pause(self, flag: bool) -> None:
        """
        Active ou désactive la mise en pause de l'enregistrement.

        Args:
            flag (bool): True pour mettre en pause, False pour reprendre.
        """
        self.pause = flag

    def is_pause(self) -> bool:
        """
        Vérifie si l'enregistrement est actuellement en pause.

        Returns:
            bool: True si en pause, sinon False.
        """
        return self.pause

    def bytes_to_float_array(self, audio_bytes: bytes) -> np.ndarray:
        """
        Convertit des données audio (bytes) en tableau de floats normalisés.

        Args:
            audio_bytes (bytes): Les données audio brutes.

        Returns:
            np.ndarray: Données audio normalisées en float32.
        """
        raw_data = np.frombuffer(buffer=audio_bytes, dtype=np.int16)
        return raw_data.astype(np.float32) / 32768.0

    def play_file(self, filename: str, listen: bool = False) -> None:
        """
        Lit un fichier audio et envoie les données au serveur.

        Args:
            filename (str): Chemin du fichier .wav à lire.
            listen (bool): Si True, joue l'audio localement aussi.
        """
        with wave.open(filename, "rb") as wavfile:
            stream = self.p.open(
                format=self.p.get_format_from_width(wavfile.getsampwidth()),
                channels=wavfile.getnchannels(),
                rate=wavfile.getframerate(),
                input=True,
                output=True,
                frames_per_buffer=self.chunk,
            )
            try:
                while self.recording:
                    data = wavfile.readframes(self.chunk)
                    if data == b"":
                        break
                    audio_array = self.bytes_to_float_array(data)
                    self.send_packet_to_server(audio_array.tobytes())
                    if listen:
                        stream.write(data)
                wavfile.close()
                self.wait_before_disconnect()
                self.send_packet_to_server(Client.END_OF_AUDIO.encode("utf-8"))
                stream.close()
                self.close_websocket()
            except KeyboardInterrupt:
                wavfile.close()
                stream.stop_stream()
                stream.close()
                self.p.terminate()
                self.close_websocket()

    def record(self) -> None:
        """
        Enregistre l'audio depuis le micro et envoie les données au serveur en temps réel.
        Gère aussi la sauvegarde locale si activée.
        """
        n_audio_file = 0
        try:
            stream = self.p.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk,
            )
            while self.recording:
                if not self.pause:
                    data = stream.read(self.chunk, exception_on_overflow=False)
                    self.frames += data
                    audio_array = self.bytes_to_float_array(data)
                    self.send_packet_to_server(audio_array.tobytes())
                    if len(self.frames) > 60 * self.rate:
                        if self.save_output_recording:
                            self.save_chunk(n_audio_file)
                            n_audio_file += 1
                        self.frames = b""
            self.finalize_recording(n_audio_file, stream)
        except KeyboardInterrupt:
            self.finalize_recording(n_audio_file, stream)

    def save_chunk(self, index: int) -> None:
        """
        Sauvegarde une portion d'enregistrement en fichier temporaire .wav.

        Args:
            index (int): Numéro d'index du fichier à sauvegarder.
        """
        t = threading.Thread(
            target=self.write_audio_frames_to_file,
            args=(self.frames[:], os.path.join(self.chunk_dir, f"{index}.wav")),
        )
        t.start()

    def write_audio_frames_to_file(self, frames: bytes, file_name: str) -> None:
        """
        Écrit des frames audio dans un fichier .wav.

        Args:
            frames (bytes): Données audio à écrire.
            file_name (str): Nom du fichier de destination.
        """
        with wave.open(file_name, "wb") as wavfile:
            wavfile.setnchannels(self.channels)
            wavfile.setsampwidth(2)
            wavfile.setframerate(self.rate)
            wavfile.writeframes(frames)

    def finalize_recording(self, n_audio_file: int, stream: Any) -> None:
        """
        Finalise l'enregistrement : écrit les dernières frames, ferme le flux et la WebSocket.

        Args:
            n_audio_file (int): Index du fichier final.
            stream (Any): Flux PyAudio à fermer.
        """
        if self.save_output_recording and len(self.frames):
            self.write_audio_frames_to_file(
                self.frames[:], os.path.join(self.chunk_dir, f"{n_audio_file}.wav")
            )
            n_audio_file += 1
        stream.stop_stream()
        stream.close()
        self.p.terminate()
        self.close_websocket()
        if self.save_output_recording:
            self.write_output_recording(n_audio_file)

    def write_output_recording(self, n_audio_file: int) -> None:
        """
        Concatène les fichiers audio intermédiaires en un seul fichier final.

        Args:
            n_audio_file (int): Nombre total de morceaux à rassembler.
        """
        input_files = [
            os.path.join(self.chunk_dir, f"{i}.wav")
            for i in range(n_audio_file)
            if os.path.exists(os.path.join(self.chunk_dir, f"{i}.wav"))
        ]
        with wave.open(self.output_recording_filename, "wb") as wavfile:
            wavfile.setnchannels(self.channels)
            wavfile.setsampwidth(2)
            wavfile.setframerate(self.rate)
            for in_file in input_files:
                with wave.open(in_file, "rb") as wav_in:
                    while True:
                        data = wav_in.readframes(self.chunk)
                        if data == b"":
                            break
                        wavfile.writeframes(data)
                os.remove(in_file)
        if os.path.exists(self.chunk_dir):
            shutil.rmtree(self.chunk_dir)

    def on_error(self, ws: websocket.WebSocketApp, error: Exception) -> None:
        """
        Méthode appelée lorsqu'une erreur WebSocket survient.

        Args:
            ws (websocket.WebSocketApp): WebSocket utilisée.
            error (Exception): L'erreur levée.
        """
        print(f"[ERROR] WebSocket Error: {error}")
        self.server_error = True
        self.error_message = error

    def on_close(self, ws: websocket.WebSocketApp, close_status_code: int, close_msg: str) -> None:
        """
        Méthode appelée à la fermeture de la connexion WebSocket.

        Args:
            ws (websocket.WebSocketApp): WebSocket utilisée.
            close_status_code (int): Code de fermeture.
            close_msg (str): Message de fermeture.
        """
        print(f"[INFO] WebSocket connection closed: {close_status_code} - {close_msg}")
        if self.call_back:
            self.recording = self.call_back(texte=None, ending=True, force=True)
        self.waiting = False

    def get_model_path(self) -> str:
        """
        Retourne le chemin du modèle utilisé.

        Returns:
            str: Chemin du modèle chargé.
        """
        return self.model_path
    
    def send_end_of_audio_signal(self) -> None:
        """
        Envoie le signal de fin d'audio au serveur TensorRT.
        """
        try:
            self.send_packet_to_server(Client.END_OF_AUDIO.encode("utf-8"))
            print("[INFO] Signal END_OF_AUDIO envoyé au serveur.")
        except Exception as e:
            print(f"[ERROR] Impossible d'envoyer END_OF_AUDIO : {e}")
