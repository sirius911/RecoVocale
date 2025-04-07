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
    """Prints formatted transcript text."""
    wrapper = textwrap.TextWrapper(width=60)
    for line in wrapper.wrap(text="".join(text)):
        print(f"[{line}]")

def resample(file: str, sr: int = 16000):
    """
    # https://github.com/openai/whisper/blob/7858aa9c08d98f75575035ecd6481f462d66ca27/whisper/audio.py#L22
    Open an audio file and read as mono waveform, resampling as necessary,
    save the resampled audio

    Args:
        file (str): The audio file to open
        sr (int): The sample rate to resample the audio if necessary

    Returns:
        resampled_file (str): The resampled audio file
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

def needs_resample(filepath, target_rate=16000):
    """
    Vérifie si un fichier WAV est déjà en 16kHz, mono, 16 bits PCM.

    Args:
        filepath (str): Chemin du fichier WAV.
        target_rate (int): Fréquence attendue (par défaut : 16000).

    Returns:
        bool: True s'il faut le resampler, False s'il est déjà conforme.
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

def remove_audio_file(file):
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
