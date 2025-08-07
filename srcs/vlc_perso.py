import os
import pathlib
import subprocess
import time
import socket
import ctypes
import ctypes.wintypes as wt
from utils import FFMPEG_PATH


class VLC:
    PIPE = "recovocale_pipe"
    DEFAULT_PORT = 4212

    def __init__(self):
        self.vlc_path = r"C:\Program Files\VideoLAN\VLC\vlc.exe"   # ou simplement "vlc" si %PATH%
        self.vlc_dir = pathlib.Path(self.vlc_path).parent
        self.plugin_dir = self.vlc_dir / "plugins"
        self.sock = None
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

        # 2) Vérifier l'interface RC
        if not self._wait_for_rc_port():
            # échec → on nettoie et on signale False
            self.proc.terminate()
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self.proc = None
            return False

        # 3) Connexion socket
        self._connect_socket()
        self.playing = False
        return True

    def _wait_for_rc_port(self, timeout=10):
        print(f"Attente démarrage RC sur le port {VLC.DEFAULT_PORT}...", flush=True)
        start = time.time()
        while time.time() - start < timeout:
            try:
                s = socket.create_connection(("localhost", VLC.DEFAULT_PORT), timeout=1)
                s.close()
                print("RC prêt", flush=True)
                return True
            except (ConnectionRefusedError, OSError):
                time.sleep(0.2)
        print("⚠️  Interface RC non disponible après %.1f s" % timeout, flush=True)
        return False

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

    def _vlc_is_actually_playing(self) -> bool:
        """
        Retourne True si VLC est réellement en lecture.
        Utilise la commande 'is_playing' du RC (1 = play, 0 = pause/stop).
        """
        if not self.is_open():
            return False

        # 1) vider le buffer éventuel
        self.sock.setblocking(False)
        try:
            while self.sock.recv(4096):
                pass
        except BlockingIOError:
            pass
        finally:
            self.sock.setblocking(True)

        # 2) envoyer la commande
        self._rc("is_playing")

        deadline = time.time() + 0.5    # 500 ms max pour recevoir "0" ou "1"
        buf = b""
        while time.time() < deadline:
            try:
                buf += self.sock.recv(4096)
            except socket.timeout:
                continue

            for token in buf.decode(errors="ignore").split():
                if token.strip() in ("0", "1"):
                    return token.strip() == "1"

        # par défaut, on considère que ça ne joue pas
        return False

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
        """
        Bascule entre lecture et pause.
        - Retourne False si VLC n'est pas lancé.
        - Ne relance ffmpeg que si nécessaire.
        """
        if not self.is_open():
            print("⚠️  play_pause() : VLC n'est pas lancé.")
            return False
        self.playing = not self.playing
        self._rc("pause")
        if self.playing:
            # if not self._vlc_is_actually_playing():
            #     self._rc("pause")
            self.start_ffmpeg_pipe()      # relance ffmpeg depuis la position courante
        else:
            # if self._vlc_is_actually_playing():
            #     self._rc("pause")
            self.stop_ffmpeg_pipe()

    def stop_ffmpeg_pipe(self):
        if getattr(self, "ffmpeg_proc", None):
            self.ffmpeg_proc.terminate()
            try:
                self.ffmpeg_proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.ffmpeg_proc.kill()
                try:
                    self.ffmpeg_proc.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    print("⚠️  ffmpeg ne répond toujours pas ; on continue.")
            finally:
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
            if getattr(self, "sock", None):
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
        if not self._wait_pipe_ready():
            return
        t0 = self.get_time()
        print(f"Lancement ffmpeg depuis {t0} s")

        # pipe_path = r"\\.\pipe\recovocale_pipe"
        # source = self.source

        cmd = [
            FFMPEG_PATH, "-loglevel", "warning", "-y",
            "-re",
            "-ss", str(t0),  # ← -ss avant -i   (fast-seek)
            "-i", self.source,
            "-vn", "-ac", "1", "-ar", "16000",
            "-sample_fmt", "s16", "-f", "s16le",
            r"\\.\pipe\recovocale_pipe"
        ]

        # Lance le ffmpeg en arrière-plan (il écrit vers le pipe)
        self.ffmpeg_proc = subprocess.Popen(cmd)

    def _wait_pipe_ready(self, name: str = r"\\.\pipe\recovocale_pipe", timeout: float = 5.0) -> bool:
        """
        Attend qu’un serveur Named-Pipe soit prêt.
        Retourne True si OK, False si délai dépassé.
        Ne lève plus d’exception bloquante.
        """
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        WaitNamedPipeW = k32.WaitNamedPipeW
        WaitNamedPipeW.argtypes = [ctypes.c_wchar_p, wt.DWORD]
        WaitNamedPipeW.restype = wt.BOOL

        deadline = time.time() + timeout
        while time.time() < deadline:
            if WaitNamedPipeW(ctypes.c_wchar_p(name), 200):   # test 200 ms
                return True
            time.sleep(0.05)                                  # laisse respirer Tk

        print(f"Pipe {name} toujours indisponible après {timeout} s")
        return False
