import ctypes
import os
import json
import time
from ctypes import c_char_p, c_uint, c_bool
import uuid

from Correcteur import intercept, corrige_ponctuation, corriger_texte


PATH_LIB = "C:/Users/lorcyr/recovocale_engine/target/release/recovocale_engine.dll"


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

        self.dll_path = os.path.abspath(PATH_LIB)
        self.ip = ip
        self.port = port
        self.json_config = json.dumps(options).encode("utf-8")

        self.lib = ctypes.CDLL(self.dll_path)

        # Signatures des fonctions
        self.lib.init.argtypes = [c_char_p, c_uint, c_char_p]
        self.lib.init.restype = None
        self.lib.is_connected.restype = c_bool
        self.lib.is_capturing.restype = c_bool
        self.lib.get_last_completed_segment.restype = ctypes.POINTER(ctypes.c_char)
        self.lib.get_last_partial_segment.restype = ctypes.POINTER(ctypes.c_char)
        self.lib.get_all_completed_segments.restype = ctypes.POINTER(ctypes.c_char)
        self.lib.get_all_completed_segments_with_number.restype = ctypes.POINTER(ctypes.c_char)
        self.lib.is_task_completed.argtypes = []
        self.lib.is_task_completed.restype = c_bool
        self.lib.clear_completed_segments.argtypes = []
        self.lib.clear_completed_segments.restype = None
        self.lib.start_capture.argtypes = []
        self.lib.stop_capture.argtypes = []
        self.lib.start_receiving_segments.argtypes = []
        self.lib.stop_receiving_segments.argtypes = []
        self.lib.send_end_of_audio.argtypes = []
        self.lib.disconnect_server.argtypes = []
        self.lib.destroy.argtypes = []
        self.lib.free_cstring.argtypes = [c_char_p]
        self.lib.free_cstring.restype = None

        self.transcription_totale = {}
        self.transcription_en_cours = ""
        self.texte_merge = ""

    def connect(self):
        self.lib.init(self.ip.encode(), self.port, self.json_config)
        for _ in range(10):
            if self.lib.is_connected():
                self.lib.start_receiving_segments()
                return True
            time.sleep(0.5)
        return False

    def is_connected(self) -> bool:
        return self.lib.is_connected()

    def is_capturing(self) -> bool:
        return self.lib.is_capturing()

    def start(self):
        if self.is_connected():
            self.lib.start_capture()

    def wait_transcription_en_cours(self, timer=1.0):
        start = time.time()
        while not self.is_transcription_terminee():
            if (time.time()-start) > timer:
                return False
            time.sleep(0.2)
        return True

    def stop(self):
        if self.is_connected():
            self.wait_transcription_en_cours(1.0)
            self.lib.stop_capture()

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

    def send_end_of_audio(self):
        self.lib.send_end_of_audio()

    def disconnect(self):
        self.lib.stop_receiving_segments()
        time.sleep(1)
        self.lib.disconnect_server()
        self.lib.destroy()

    def is_transcription_terminee(self) -> bool:
        return self.lib.is_task_completed()

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
        self._add(self.get_completed())
        self.transcription_en_cours = self.get_partial()

    def get(self, insertions, dico=False) -> str:
        self._update()
        chaine = " ".join(self.transcription_totale.keys())

        text_apres_insertion, insertion = intercept(chaine, insertions.get())
        text_apres_insertion += f" {self.transcription_en_cours}"
        text_apres_ponctuation = corrige_ponctuation(text_apres_insertion)
        if dico:
            text_to_copy = corriger_texte(text_apres_ponctuation)
        else:
            text_to_copy = text_apres_ponctuation
        self.texte_merge = text_to_copy
        if insertion:
            self.wait_transcription_en_cours(1.0)
            self.clear_transcriptions()
            self.merge()

        return text_to_copy

    def print_transcriptions_lignes(self):
        for i, phrase in enumerate(self.transcription_totale.keys()):
            print(f"{i} -> {phrase}")
        if self.transcription_en_cours:
            print(f"il reste [{self.transcription_en_cours}]")
        else:
            print("partial vide")

    def merge(self):
        self.transcription_totale.clear()
        print(f"Je dois merger [{self.texte_merge}]", flush=True)
        self._add(self.texte_merge)

    def clear(self) -> None:
        self.wait_transcription_en_cours()
        self.clear_transcriptions()
        self.transcription_totale = {}
        self.transcription_en_cours = ""
        self.texte_merge = ""

    def set(self, texte) -> None:
        self.texte_merge = texte
        self.merge()
