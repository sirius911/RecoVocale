import os
import pathlib
import subprocess


class VLC:
    PIPE = "recovocale_pipe"

    def __init__(self):
        self.vlc_path = r"C:\Program Files\VideoLAN\VLC\vlc.exe"   # ou simplement "vlc" si %PATH%
        self.vlc_dir = pathlib.Path(self.vlc_path).parent
        self.plugin_dir = self.vlc_dir / "plugins"
        self.sout = (
            "#transcode{acodec=s16l,channels=1,samplerate=16000}:"
            "duplicate{dst=file{dst=\\\\\\\\\\.\\\\pipe\\\\recovocale_pipe,mux=raw},dst=display}"
        )
        self.proc = None
        self.source = None

    def open(self, source: str):
        if self.proc:
            print("VLC déjà lancé", flush=True)
            return
        self.source = source
        vlc_cmd = [
            self.vlc_path,
            f"--sout={self.sout}",
            "--sout-keep",
            "--quiet",
            "-vv",
            "--file-logging",
            "--start-paused",
            # "--extraintf", "rc",        # ← interface Remote-Control
            # "--rc-fake-tty",
            # "--plugin-path", str(self.plugin_dir),
            "--",
            str(pathlib.Path(source)),
        ]
        env = os.environ.copy()
        env["VLC_PLUGIN_PATH"] = str(self.plugin_dir)
        env["PATH"] = str(self.vlc_dir) + os.pathsep + env["PATH"]

        print("Lancement VLC :", vlc_cmd, flush=True)
        print(f"vlc_dir = {self.vlc_dir}")
        self.proc = subprocess.Popen(
            vlc_cmd,
            cwd=self.vlc_dir,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            text=True,                    # stdin en mode texte
            creationflags=0          # fenêtre visible
        )

    # ------------------------------------------------------------------ #
    # ↓↓↓ Commandes runtime ↓↓↓ ---------------------------------------- #
    def _rc(self, command: str) -> None:
        if not (self.proc and self.proc.stdin):
            raise RuntimeError("VLC non lancé")
        try:
            self.proc.stdin.write(command + "\n")
            self.proc.stdin.flush()
        except BrokenPipeError:
            pass  # VLC est déjà fermé

    def play_pause(self) -> None:
        """Alterne play / pause."""
        self._rc("pause")

    def stop(self) -> None:
        """Stoppe la lecture (mais ne ferme pas VLC)."""
        self._rc("stop")

    def seek(self, seconds: int) -> None:
        """Avance/recule de `seconds` (positif ou négatif)."""
        self._rc(f"seek {seconds}")

    # ------------------------------------------------------------------ #

    def close(self):
        print("Close de VLC ...", end=" ", flush=True)
        if self.proc is not None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self.proc = None
        print("OK", flush=True)

    def is_open(self):
        return self.proc is not None
