import textwrap
import scipy
import ffmpeg
import numpy as np
import sys
import os
import wave
import contextlib

if getattr(sys, 'frozen', False):
    # Programme compilé → on utilise le dossier de l'exécutable
    BASE_PATH = os.path.dirname(sys.executable)
else:
    # Exécution normale (non compilée)
    BASE_PATH = os.path.dirname(__file__)

FFMPEG_PATH = os.path.join(BASE_PATH, "bin", "ffmpeg.exe")


def print_transcript(text):
    """
    Affiche un texte de transcription formaté en lignes de 60 caractères.

    Args:
        text (str | list[str]): Texte à afficher (chaîne ou liste de segments).
    """

    wrapper = textwrap.TextWrapper(width=60)
    for line in wrapper.wrap(text="".join(text)):
        print(f"[{line}]")


def resample(file: str, sr: int = 16000) -> str:
    """
    Ouvre un fichier audio, le convertit en mono 16 bits PCM et le resample à la fréquence donnée.
    https://github.com/openai/whisper/blob/7858aa9c08d98f75575035ecd6481f462d66ca27/whisper/audio.py#L22

    Utilise `ffmpeg` pour effectuer le traitement et enregistre le résultat en `.wav`.

    Args:
        file (str): Chemin du fichier audio original.
        sr (int): Fréquence cible (par défaut : 16000 Hz).

    Returns:
        str: Chemin du fichier audio resamplé.
    """

    try:
        # This launches a subprocess to decode audio while down-mixing and resampling as necessary.
        # Requires the ffmpeg CLI and `ffmpeg-python` package to be installed.
        out, _ = (
            ffmpeg.input(file, threads=0)
            .output("-", format="s16le", acodec="pcm_s16le", ac=1, ar=sr)
            .run(cmd=[FFMPEG_PATH, "-nostdin"], capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as e:
        raise RuntimeError(f"Failed to load audio: {e.stderr.decode()}") from e
    np_buffer = np.frombuffer(out, dtype=np.int16)

    resampled_file = f"{file.split('.')[0]}_resampled.wav"
    scipy.io.wavfile.write(resampled_file, sr, np_buffer.astype(np.int16))
    print(f"[utils] Fichier resamplé : {resampled_file}")
    return resampled_file


def needs_resample(filepath: str, target_rate: int = 16000) -> bool:
    """
    Vérifie si un fichier audio doit être resamplé en 16 kHz, mono, 16 bits.

    Args:
        filepath (str): Chemin vers le fichier .wav.
        target_rate (int): Fréquence souhaitée (default = 16000 Hz).

    Returns:
        bool: True si le fichier ne respecte pas les critères et doit être resamplé.
    """

    try:
        with contextlib.closing(wave.open(filepath, 'rb')) as wf:
            nchannels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()

            if nchannels != 1:
                return True
            if sampwidth != 2:
                return True  # 2 bytes = 16 bits
            if framerate != target_rate:
                return True
            return False
    except Exception as e:
        print(f"[utils] Erreur lors de la vérification du fichier audio : {e}")
        return False


def remove_audio_file(file: str) -> bool:
    """
    Supprime un fichier audio s’il existe, avec gestion d’erreur.

    Args:
        file (str): Chemin du fichier à supprimer.

    Returns:
        bool: True si la suppression a réussi ou que le fichier n'existe pas, False sinon.
    """

    """
    Supprime le fichier audio spécifié.

    Args:
        file (str): Chemin du fichier à supprimer.
    """
    try:
        if os.path.exists(file):
            os.remove(file)
            print(f"[utils] Fichier supprimé : {file}")
        else:
            print(f"[utils] Le fichier n'existe pas : {file}")
    except Exception as e:
        print(f"[utils] Erreur lors de la suppression du fichier : {e}")
        return False
    return True
