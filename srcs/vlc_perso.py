import os
import pathlib
import subprocess
import time
import socket
from utils import FFMPEG_PATH


class VLC:
    PIPE = "recovocale_pipe"
    DEFAULT_PORT = 4212

    def __init__(self):
        self.vlc_path = r"C:\Program Files\VideoLAN\VLC\vlc.exe"   # ou simplement "vlc" si %PATH%
        self.vlc_dir = pathlib.Path(self.vlc_path).parent
        self.plugin_dir = self.vlc_dir / "plugins"
        # self.sout = (
        #     "#transcode{vcodec=none,acodec=s16l,channels=1,samplerate=16000}:"
        #     "duplicate{dst=file{dst=\\\\\\\\\\.\\\\pipe\\\\recovocale_pipe,mux=raw},dst=display}"
        # )
        self.proc = None
        self.source = None
        self.playing = False

    def open(self, source: str = None):
        if self.proc:
            print("VLC déjà lancé", flush=True)
            return
        self.source = source
        vlc_cmd = [
            self.vlc_path,
            # f"--sout={self.sout}",
            # "--sout-keep",
            "--quiet",
            "-vv",
            # "--file-logging",
            "--start-paused",
            "--extraintf=rc",        # ← interface Remote-Control
            "--rc-quiet",
            f"--rc-host=localhost:{VLC.DEFAULT_PORT}",
            # "--",
            # str(pathlib.Path(source)),
        ]
        # Ajoute le fichier si présent
        if source:
            vlc_cmd.extend(["--", str(pathlib.Path(source))])

        env = os.environ.copy()
        env["VLC_PLUGIN_PATH"] = str(self.plugin_dir)
        env["PATH"] = str(self.vlc_dir) + os.pathsep + env["PATH"]

        # print("Lancement VLC :", vlc_cmd, flush=True)
        self.proc = subprocess.Popen(
            vlc_cmd,
            cwd=self.vlc_dir,
            env=env,
        )

        # Attendre que VLC écoute sur le port
        self._wait_for_rc_port()
        self._connect_socket()
        self.playing = False

    def _wait_for_rc_port(self, timeout=10):
        print(f"Attente démarrage RC sur le port {VLC.DEFAULT_PORT}...", flush=True)
        start = time.time()
        while time.time() - start < timeout:
            try:
                s = socket.create_connection(("localhost", VLC.DEFAULT_PORT), timeout=1)
                s.close()
                print("RC prêt", flush=True)
                return
            except (ConnectionRefusedError, OSError):
                time.sleep(0.2)
        raise RuntimeError("VLC RC interface n'est pas disponible")

    def _connect_socket(self):
        print("Connexion RC socket...", flush=True)
        self.sock = socket.create_connection(("localhost", VLC.DEFAULT_PORT))
        self.sock.settimeout(0.5)  # non bloquant
        # Vider le buffer d'accueil si besoin
        try:
            self.sock.recv(4096)
        except Exception:
            pass
        print("Socket connectée", flush=True)

    # ------------------------------------------------------------------ #
    # ↓↓↓ Commandes runtime ↓↓↓ ---------------------------------------- #
    def _rc(self, command: str):
        if not self.sock:
            raise RuntimeError("RC non connecté")
        try:
            print(f"Envoi RC: {command}")
            self.sock.sendall((command.strip() + "\n").encode("utf-8"))
            # Optionnel : lire la réponse si tu veux (non bloquant)
            try:
                rep = self.sock.recv(4096)
                print("Réponse RC:", rep)
            except socket.timeout:
                pass
        except (BrokenPipeError, ConnectionResetError, OSError):
            print("Erreur lors de l'envoi RC")

    def play_pause(self):
        self._rc("pause")
        self.playing = not self.playing
        if self.playing:
            self.start_ffmpeg_pipe()      # relance ffmpeg depuis la position courante
        else:
            self.stop_ffmpeg_pipe()

    def stop_ffmpeg_pipe(self):
        if getattr(self, "ffmpeg_proc", None):
            self.ffmpeg_proc.terminate()
            try:
                rc = self.ffmpeg_proc.wait(timeout=2)   # ← laisse le temps de fermer le pipe
                print(f"ffmpeg exited with {rc}")
            except subprocess.TimeoutExpired:
                self.ffmpeg_proc.kill()
                self.ffmpeg_proc.wait()
            except Exception as e:
                print(f"[Exception] stop_ffmpeg(): {e}")
            self.ffmpeg_proc = None

    def seek(self, seconds: int):
        self._rc(f"seek {seconds}")
        time.sleep(0.05)
        if self.playing:
            self.stop_ffmpeg_pipe()
            self.start_ffmpeg_pipe()   # repart à vitesse temps-réel

    # ------------------------------------------------------------------ #

    def close(self):
        print("Fermeture de VLC...", end=" ", flush=True)
        self.stop_ffmpeg_pipe()
        try:
            if self.sock:
                try:
                    self._rc("stop")
                    # Essaye de quitter proprement (rarement fonctionne sous Windows)
                    self._rc("quit")
                except Exception:
                    pass
                try:
                    self.sock.close()
                except Exception:
                    pass
                self.sock = None
            if self.proc is not None:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
                self.proc = None
            print("OK", flush=True)
        except Exception as e:
            print(e)
        self.playing = False

    def is_open(self):
        return self.proc is not None

    def is_playing(self) -> bool:
        return self.playing

    def get_time(self) -> int:
        """Renvoie la position courante (en secondes) en évitant les lignes parasite."""

        # 1) vidage du buffer existant
        self.sock.setblocking(False)
        try:
            while True:
                if not self.sock.recv(4096):
                    break
        except BlockingIOError:
            pass
        finally:
            self.sock.setblocking(True)

        # 2) envoi de la commande
        self._rc("get_time")

        deadline = time.time() + 1.0  # 1 s max
        buf = b""
        while time.time() < deadline:
            try:
                buf += self.sock.recv(4096)
            except socket.timeout:
                continue

            for line in buf.decode(errors="ignore").splitlines():
                if line.strip().isdigit():
                    return int(line.strip())

        # si rien de numérique : on renvoie 0 par défaut
        return 0

    def start_ffmpeg_pipe(self):
        time.sleep(0.10)
        t0 = self.get_time()
        print(f"Lancement ffmpeg depuis {t0} s")

        # pipe_path = r"\\.\pipe\recovocale_pipe"
        # source = self.source

        cmd = [
            FFMPEG_PATH, "-loglevel", "warning", "-y",
            "-re",
            "-ss", str(t0),             #     ← -ss avant -i   (fast-seek)
            "-i", self.source,
            "-vn", "-ac", "1", "-ar", "16000",
            "-sample_fmt", "s16", "-f", "s16le",
            r"\\.\pipe\recovocale_pipe"
        ]

        # Lance le ffmpeg en arrière-plan (il écrit vers le pipe)
        self.ffmpeg_proc = subprocess.Popen(cmd)
