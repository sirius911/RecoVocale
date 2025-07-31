import ctypes
import os
import json
import sys
import time
from ctypes import c_char_p, c_uint, c_bool
import uuid
from info import VERSION_DLL
from Correcteur import intercept, corrige_ponctuation, corriger_texte
from loger import compter_mots
from vlc_perso import VLC


def vide(chaine: str) -> bool:
    return all(c == " " for c in chaine)


PATH_LIB = "C:/Users/lorcyr/recovocale_engine/target/release/recovocale_engine.dll"


def get_dll_path():
    if getattr(sys, 'frozen', False):
        # Exécutable compilé (PyInstaller)
        base_path = os.path.dirname(sys.executable)
        dll_path = os.path.join(base_path, 'bin', 'recovocale_engine.dll')
    else:
        # En mode développement (exécution Python)
        dll_path = PATH_LIB
    return dll_path


class RecoVocaleClientEngine:
    def __init__(self, ip, port, ip_client, options=None):

        if options is None:
            options = {
                "uid": str(uuid.uuid4()),
                "language": "fr",
                "task": "transcribe",
                "model": "large-v3",
                "use_vad": True,
                "ip_client": ip_client,
                "beam_size": 5,
                "best_of": 1,
                "patience": 0.5,
                "length_penalty": 1.0,
                "repetition_penalty": 1.5,
                "no_repeat_ngram_size": 3,
                "log_prob_threshold": -1.0,
                "no_speech_threshold": 0.3,
                "compression_ratio_threshold": 1.2,
                "condition_on_previous_text": False,
                "temperature": [0.2, 0.4],
                "initial_prompt": "Rapport médical",
            }
        else:
            options['uid'] = str(uuid.uuid4())
            options['ip_client'] = ip_client

        self.dll_path = get_dll_path()
        self.ip = ip
        self.port = port
        self.backend = None
        self.model = None
        self.json_config = json.dumps(options).encode("utf-8")

        if not os.path.exists(self.dll_path):
            raise FileNotFoundError(f"DLL manquante : {self.dll_path}")

        self.lib = ctypes.CDLL(self.dll_path)
        # Pour le debug
        self.lib.init_panic_hook.argtypes = []
        self.lib.init_panic_hook.restype = None
        self.lib.init_panic_hook()  # debugRecoVocaleClientEngine que tu as déjà

        # Signatures des fonctions
        self.lib.get_version.restype = ctypes.c_char_p
        self.version_dll = self.lib.get_version().decode()
        if self.version_dll != VERSION_DLL:
            raise RuntimeError(
                f"Mauvaise version du DLL : {self.version_dll}. "
                f"Requise : {VERSION_DLL}"
            )
        self.lib.init.argtypes = [c_char_p, c_uint, c_char_p]
        self.lib.init.restype = None

        self.lib.is_connected.argtypes = []
        self.lib.is_capturing.argtypes = []
        self.lib.is_task_in_progress.argtypes = []
        self.lib.is_connected.restype = c_bool
        self.lib.is_capturing.restype = c_bool
        self.lib.is_task_in_progress.restype = c_bool

        self.lib.get_last_completed_segment.restype = ctypes.POINTER(ctypes.c_char)
        self.lib.get_last_partial_segment.restype = ctypes.POINTER(ctypes.c_char)
        self.lib.get_all_completed_segments.restype = ctypes.POINTER(ctypes.c_char)
        self.lib.get_all_completed_segments_with_number.restype = ctypes.POINTER(ctypes.c_char)
        self.lib.get_backend.restype = ctypes.POINTER(ctypes.c_char)
        self.lib.get_model.restype = ctypes.POINTER(ctypes.c_char)
        self.lib.is_task_completed.argtypes = []
        self.lib.is_task_completed.restype = c_bool
        self.lib.clear_completed_segments.argtypes = []
        self.lib.clear_completed_segments.restype = None
        self.lib.start_capture.argtypes = [c_char_p]
        self.lib.start_capture.restype = None
        self.lib.start_capture_audio_file.argtypes = [c_char_p, c_bool]
        self.lib.start_capture_audio_file.restype = None
        self.lib.stop_capture.argtypes = []
        self.lib.stop_capture_audio_file.argtypes = []
        self.lib.start_receiving_segments.argtypes = []
        self.lib.stop_receiving_segments.argtypes = []
        self.lib.send_end_of_audio.argtypes = []
        self.lib.disconnect_server.argtypes = []
        self.lib.destroy.argtypes = []
        self.lib.free_cstring.argtypes = [c_char_p]
        self.lib.free_cstring.restype = None
        self.lib.start_capture_pipe.argtypes = [c_char_p, c_bool]
        self.lib.start_capture_pipe.restype = None

        self.lib.stop_capture_pipe.argtypes = []
        self.lib.stop_capture_pipe.restype = None
        self.pipe = False

        self.transcription_totale = {}
        self.transcription_en_cours = ""
        self.texte_merge = ""

        self.nb_mots_trancripts = 0
        print(f"Chargement dll version {self.version_dll}")

    def connect(self):
        if self.is_connected():
            return True
        self.lib.init(self.ip.encode(), self.port, self.json_config)

        for _ in range(10):
            if self.lib.is_connected():
                self.backend = self.get_backend()
                self.model = self.get_model()
                self.lib.start_receiving_segments()
                return True
            time.sleep(0.5)
        return False

    def restart_connection(self, ip: str, port: int) -> bool:
        """
        Coupe proprement la capture (si nécessaire), se déconnecte
        et se reconnecte au serveur WhisperLive avec la nouvelle IP/Port.

        Args:
            ip (str): Adresse IP du nouveau serveur.
            port (int): Port du nouveau serveur.

        Returns:
            bool: True si la reconnexion a réussi, False sinon.
        """
        # 1) Arrêter toute capture en cours
        if self.is_capturing():
            self.stop()

        # 2) Se déconnecter du serveur courant
        if self.is_connected():
            self.disconnect()

        # 3) Mettre à jour les paramètres réseau
        self.ip = ip
        self.port = port

        # 4) Recréer la connexion et démarrer la réception des segments
        return self.connect()

    def is_connected(self) -> bool:
        return self.lib.is_connected()

    def is_capturing(self) -> bool:
        ret: bool = self.lib.is_capturing()
        return ret

    def start(self, file_temp=None, file_to_capture=None, listen=True):
        if file_temp is not None:
            print(f"enregistre dans {file_temp}")
            file_temp = file_temp.encode('utf-8')
        if self.is_connected():
            if file_to_capture is None:
                self.lib.start_capture(file_temp)
            else:
                # TODO Verifier la présence du fichier
                self.start_audio_file(audio_path=file_to_capture, listen=listen)

    def wait_transcription_en_cours(self, timer=1.0):
        start = time.time()
        while not self.is_transcription_terminee():
            self._update()
            if (time.time()-start) > timer:
                return False
            time.sleep(0.2)
        return True

    def wait_connected(self, timer=5.0):
        start = time.time()
        while not self.lib.is_connected():
            if (time.time()-start) > timer:
                return False
            time.sleep(0.2)
        return True

    def stop(self, audio_file=None):
        if self.is_connected():
            if audio_file is not None:
                self.lib.stop_capture_audio_file()
            elif self.pipe:
                self.stop_audio_pipe()
            else:
                self.lib.stop_capture()
                self.send_end_of_audio()

            self.wait_transcription_en_cours(3.0)

    def get_string_and_free(self, getter_func):
        ptr = getter_func()
        if ptr:
            try:
                return ctypes.cast(ptr, ctypes.c_char_p).value.decode()
            finally:
                self.lib.free_cstring(ptr)
        return None

    def get_partial(self) -> str:
        chaine = self.get_string_and_free(self.lib.get_last_partial_segment)
        if chaine is not None:
            # print(f"PARTIAL_SEGMENT = {chaine}", flush=True)
            return chaine
        else:
            return ""

    def get_completed(self) -> str:
        chaine = self.get_string_and_free(self.lib.get_last_completed_segment)
        if chaine is not None:
            # print(f"LAST_COMPLETED = {chaine}", flush=True)
            return chaine
        else:
            return ""

    def get_all_completed(self) -> str:
        chaine = self.get_string_and_free(self.lib.get_all_completed_segments)
        if chaine is not None:
            return chaine
        else:
            return ""

    def get_backend(self) -> str:
        chaine = self.get_string_and_free(self.lib.get_backend)
        if chaine is not None:
            return chaine
        else:
            return "None"

    def get_model(self) -> str:
        chaine = self.get_string_and_free(self.lib.get_model)
        if chaine is not None:
            return chaine
        else:
            return "None"

    def send_end_of_audio(self):
        self.lib.send_end_of_audio()

    def disconnect(self):
        self.lib.stop_receiving_segments()
        time.sleep(1)
        self.lib.disconnect_server()
        self.lib.destroy()

    def is_transcription_terminee(self) -> bool:
        return self.lib.is_task_completed() and not self.lib.is_task_in_progress()

    def clear_transcriptions(self) -> None:
        self.lib.clear_completed_segments()

    def print_all_segments(self, flush=True) -> None:
        chaine = self.get_string_and_free(self.lib.get_all_completed_segments_with_number)
        print("LAST_SEGMENTs : ", chaine, flush=flush)
        print(f"PARTIAL_SEGMENT [{self.get_partial()}]", flush=flush)

    def _add(self, phrase):
        if phrase and phrase not in self.transcription_totale:
            self.transcription_totale[phrase] = None

    def _update(self) -> None:
        self.transcription_en_cours = self.get_partial()
        chaine = self.get_completed()
        if not vide(chaine):
            self._add(chaine)
            # print(f"len(transcription_totale) = {len(self.transcription_totale)}")

    def get_reduit(self):
        # On renvoi text , flag completed
        self._update()
        # essais
        return self.transcription_en_cours, self.transcription_totale.keys()
        # if self.transcription_en_cours:
        #     return self.transcription_en_cours, False
        # ret = ""
        # if self.transcription_totale:
        #     ret = list(self.transcription_totale.keys())[-1]
        # return ret, True

    def get(self, insertions, dico=False) -> str:
        self._update()
        chaine = " ".join(self.transcription_totale.keys())
        # if vide(chaine):
        #     print("chaine VIDE")
        text_apres_insertion, insertion = intercept(chaine, insertions.get())
        # if vide(text_apres_insertion):
        #     print("text_apres_insertion VIDE")
        text_apres_insertion += f" {self.transcription_en_cours}"
        # if vide(text_apres_insertion):
        #     print("text_apres_insertion VIDE")
        text_apres_ponctuation = corrige_ponctuation(text_apres_insertion)
        # if vide(text_apres_ponctuation):
        #     print("text_apres_ponctuation VIDE")
        if dico:
            text_to_copy = corriger_texte(text_apres_ponctuation)
        else:
            text_to_copy = text_apres_ponctuation
        self.texte_merge = text_to_copy
        # if vide(self.texte_merge):
        #     print("self.texte_merge VIDE")
        if insertion:
            # self.wait_transcription_en_cours(1.0)
            self.merge()
            self.clear_transcriptions()
            return (f"{self.texte_merge} {self.transcription_en_cours}")
        # if vide(text_to_copy):
        #     print("text_to_copy VIDE")
        return text_to_copy

    def print_transcriptions_lignes(self):
        # pour debug
        for i, phrase in enumerate(self.transcription_totale.keys()):
            print(f"{i} -> {phrase}")
        if self.transcription_en_cours:
            print(f"il reste [{self.transcription_en_cours}]")
        else:
            print("partial vide")

    def merge(self):
        #  consiste à effacer transcription_totale et à utiliser texte merge
        print(f"Je dois merger [{self.texte_merge}]", flush=True)
        self.transcription_totale = {}
        print(f"transcription_en_cours = {self.transcription_en_cours}")
        self._add(self.texte_merge)
        return self.texte_merge

    def clear(self) -> None:
        self.wait_transcription_en_cours()
        self.clear_transcriptions()
        self.transcription_totale = {}
        self.transcription_en_cours = ""
        self.texte_merge = ""
        self.nb_mots_trancripts = 0

    def set(self, texte) -> None:
        self.clear_transcriptions()
        self.texte_merge = texte
        self.merge()

    def get_nb_mots_trancripts(self) -> int:
        nb_mots = compter_mots(phrase=self.texte_merge) - self.nb_mots_trancripts
        self.nb_mots_trancripts += nb_mots
        return nb_mots

    def start_audio_file(self, audio_path: str, listen: bool = True):
        """
        Lance la transcription à partir d'un fichier audio local (WAV/FLAC/…).
        """
        if self.pipe:
            self.start_audio_pipe()

        # encodage UTF-8 + terminaison \0 prise en charge par ctypes
        self.lib.start_capture_audio_file(audio_path.encode("utf-8"), listen)

    def start_audio_pipe(self):
        """Démarre la capture depuis un Named-Pipe Windows."""
        # pipe_name: str = "recovocale_pipe"
        if self.connect():
            if not self.pipe:
                print("start_capture_pipe()")
                self.lib.start_capture_pipe(VLC.PIPE.encode("utf-8"), False)
                self.pipe = True
        else:
            print("Client Non connecté")

    def stop_audio_pipe(self):
        self.lib.stop_capture_pipe()
        self.pipe = False
