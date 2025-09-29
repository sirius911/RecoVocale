# pip install sounddevice numpy requests
import os
import sounddevice as sd
import numpy as np
import io
import wave
import requests
import threading
import socket
import time
from urllib.parse import urlparse


class VoiceTranscriber:
    def __init__(
        self,
        server_url: str,                   # ex: "http://10.1.147.252:8000/v1/audio/transcriptions"
        api_key: str | None = None,        # si votre serveur n'en veut pas, laisser None
        language: str = "fr",
        samplerate: int = 16000,
        channels: int = 1,
        device: int | None = None,         # index du micro (None = défaut)
        timeout: int = 120,
        stt_options: dict | None = None,
        initial_prompt: str | None = None
    ):
        self.server_url = server_url.rstrip("/")
        self.api_key = api_key
        self.language = language
        self.samplerate = samplerate
        self.channels = channels
        self.device = device
        self.timeout = timeout

        self.stt_options = {
            "temperature": 0,
            "no_speech_threshold": 0.9,
            "vad_filter": True,
            "response_format": "verbose_json",          # décommenter si supporté
            "condition_on_previous_text": False,
            "beam_size": 1,
            "word_timestamps": False,
            "compute_type": "float16",                  # si supporté côté serveur
        }
        if stt_options:
            self.stt_options.update(stt_options)
        if initial_prompt:
            self.stt_options["initial_prompt"] = initial_prompt
        self._frames = []
        self._stream = None
        self._lock = threading.Lock()
        self._recording = False
        self._save_to = None
        self._health_ok = None
        self._health_ts = 0.0
        self._ttl_ok = 10.0    # recheck lent quand OK
        self._ttl_ko = 1.0     # recheck rapide quand KO
        self._health_msg = ""  # pour afficher dans debug
        print(f"VoiceTranscriber({server_url})")

    def _parse_host_port(self):
        u = urlparse(self.server_url)
        host = u.hostname or "localhost"
        port = u.port or (443 if u.scheme == "https" else 80)
        return host, port

    def set_initial_prompt(self, prompt: str | None):
        if prompt:
            self.stt_options["initial_prompt"] = prompt
        else:
            self.stt_options.pop("initial_prompt", None)

    def check_server_fast(self, timeout_connect=0.2, timeout_read=0.2):
        """
        Test ultra-rapide pour vérifier que le serveur est dispo.
        1) TCP connect court
        2) GET /openapi.json (200 attendu)
        """
        start = time.perf_counter()
        host, port = self._parse_host_port()

        # 1) TCP connect rapide
        try:
            with socket.create_connection((host, port), timeout=timeout_connect):
                pass
        except Exception as e:
            dt = int((time.perf_counter() - start) * 1000)
            return False, f"TCP fail: {e} ({dt} ms)"

        # 2) GET /openapi.json (léger)
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        base = self.server_url.rstrip("/v1")
        try:
            r = requests.get(f"{base}/openapi.json",
                             headers=headers,
                             timeout=(timeout_connect, timeout_read))
            dt = int((time.perf_counter() - start) * 1000)
            if 200 <= r.status_code < 300:
                return True, f"/openapi.json: {r.status_code} ({dt} ms)"
            return False, f"/openapi.json: HTTP {r.status_code} ({dt} ms)"
        except Exception as e:
            dt = int((time.perf_counter() - start) * 1000)
            return False, f"HTTP fail: {e} ({dt} ms)"

    def is_server_up(self, timeout: float = 0.25, ttl: float | None = None) -> bool:
        now = time.perf_counter()

        # TTL adaptatif (si l'appelant ne force pas via ttl)
        if ttl is None:
            ttl = self._ttl_ok if self._health_ok else self._ttl_ko

        if self._health_ok is not None and (now - self._health_ts) < ttl:
            return self._health_ok
        ok, msg = self.check_server_fast(timeout_connect=min(timeout, 0.25),
                                         timeout_read=min(timeout, 0.25))
        self._health_ok = ok
        self._health_ts = time.perf_counter()
        self._health_msg = msg
        return ok

    def last_health_message(self) -> str:
        return self._health_msg or ""

    @staticmethod
    def list_devices():
        """Affiche les devices disponibles."""
        for i, d in enumerate(sd.query_devices()):
            print(f"[{i}] {d['name']} - input ch: {d['max_input_channels']}")

    def _callback(self, indata, frames, time, status):
        if status:
            print("⚠️  audio status:", status)
        # indata arrive au dtype demandé; ici int16 -> pas de conversion nécessaire
        with self._lock:
            self._frames.append(indata.copy())

    def start(self, save_to: str | None = None):
        """
        Démarre l’enregistrement micro.
        Si save_to est fourni, le flux capturé sera sauvegardé en WAV à ce chemin.
        """
        self._save_to = save_to  # chemin ou None
        if self._recording:
            print("Déjà en enregistrement.")
            return
        self._frames = []
        self._stream = sd.InputStream(
            samplerate=self.samplerate,
            channels=self.channels,
            dtype='int16',
            callback=self._callback,
            device=self.device,
        )
        self._stream.start()
        self._recording = True
        # print("🎙️ Enregistrement démarré… (start)")

    def stop(self) -> str:
        if not self._recording:
            print("Pas d'enregistrement en cours.")
            return
        # Stoppe proprement le flux
        self._stream.stop()
        self._stream.close()
        self._stream = None
        self._recording = False
        # print("⏹️  Enregistrement arrêté. Préparation…")

        # Concatène les chunks
        with self._lock:
            if not self._frames:
                return ""
            audio = np.concatenate(self._frames, axis=0)

        # Encapsule en WAV en mémoire
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.samplerate)
            wf.writeframes(audio.tobytes())
        buf.seek(0)

        # Sauvegarde sur disque si demandé
        if self._save_to:
            try:
                with open(self._save_to, 'wb') as f:
                    f.write(buf.getbuffer())
                print(f"💾 Audio sauvegardé dans {self._save_to}")
            except Exception as e:
                print(f"Erreur sauvegarde WAV: {e}")
            finally:
                self._save_to = None

        # --- Options STT (anti-silence, etc.) ---
        # Si self.stt_options existe, on l'utilise ; sinon valeurs par défaut.
        stt_options = getattr(self, "stt_options", None) or {
            "temperature": 0,
            "no_speech_threshold": 0.9,
            "vad_filter": True,
            "response_format": "verbose_json",        # ← décommente si supporté par le serveur
            "condition_on_previous_text": False,
            "beam_size": 1,
            "word_timestamps": False,
            "compute_type": "float16",
        }

        # Envoi au serveur Whisper
        files = {"file": ("record.wav", buf, "audio/wav")}
        data = {"language": self.language, **stt_options}
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        url = f"{self.server_url}/audio/transcriptions"
        resp = requests.post(url, files=files, data=data, headers=headers, timeout=self.timeout)
        resp.raise_for_status()

        # Gestion du JSON + filtre silence si verbose_json
        try:
            out = resp.json()
        except Exception:
            return ""

        if stt_options.get("response_format") == "verbose_json":
            text = (out.get("text") or "").strip()
            segments = out.get("segments") or []
            # si aucun segment détecté ou texte vide → considère que c'est du silence
            return text if text and segments else ""

        return (out.get("text") or "").strip()

    def transcribe_file(self, file_path: str, language: str = "fr", max_duration: int = 180) -> str:
        """
        Envoie un fichier audio au serveur et retourne la transcription texte.
        Bloquant : à appeler dans un thread pour ne pas geler l'UI.

        Args:
            file_path (str): chemin du fichier audio.
            language (str): langue de transcription.
            max_duration (int): durée max en secondes autorisée.
        Raises:
            ValueError: si le fichier audio est plus long que max_duration.
        """
        # --- Vérification durée ---
        try:
            with wave.open(file_path, "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                duration = frames / float(rate)
                if duration > max_duration:
                    raise ValueError(f"Durée fichier {int(duration)}s > limite {max_duration}s")
        except wave.Error:
            # si ce n'est pas un wav, ignorer la vérif (ou utiliser pydub pour tous les formats)
            pass

        url = f"{self.server_url}/audio/transcriptions"  # ex: http://ip:port/v1/audio/transcriptions
        filename = os.path.basename(file_path)
        # Déduis un mimetype simple ; le serveur s’en fiche souvent, mais ça aide
        mime = "audio/wav"
        ext = os.path.splitext(filename)[1].lower()
        if ext in (".mp3",):
            mime = "audio/mpeg"
        elif ext in (".flac",):
            mime = "audio/flac"
        elif ext in (".ogg",):
            mime = "audio/ogg"
        elif ext in (".mp4", ".m4a"):
            mime = "audio/mp4"

        with open(file_path, "rb") as f:
            files = {"file": (filename, f, mime)}
            data = {"language": language}
            r = requests.post(url, files=files, data=data, timeout=120)
            r.raise_for_status()
            # Adapte si le JSON est différent
            js = r.json()
            return js.get("text", "").strip()

    @property
    def is_recording(self) -> bool:
        return self._recording


if __name__ == "__main__":
    vt = VoiceTranscriber(
        server_url="http://10.1.147.252:8000/v1",
        api_key=None,          # ou "dummy" si votre serveur l'exige
        language="fr",
        device=None            # mets un index si on veut un micro précis
    )

    # vt.list_devices()  # pour voir la liste des micros

    while True:
        cmd = input("Tape 'start' pour enregistrer, 'stop' pour transcrire, 'quit' pour sortir > ").strip().lower()
        if cmd == "start":
            vt.start()
        elif cmd == "stop":
            try:
                text = vt.stop()
                print("📝 Transcription:", text)
            except Exception as e:
                print("Erreur:", e)
        elif cmd in ("quit", "exit"):
            if vt.is_recording:
                vt.stop()
            break
        else:
            print("Commande inconnue.")
