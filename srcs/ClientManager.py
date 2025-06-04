import threading
import wave
import traceback
from tkinter import messagebox

from client import Client
from Correcteur import intercept, corrige_ponctuation
from utils_keyboard import Simulator
from info import APPRENTI


class ClientManager:
    """
    Gère la création, l'exécution et la communication avec une instance de Client (WebSocket).

    Cette classe sert d'interface entre le programme principal (RecoVocale) et le serveur
    WhisperLive. Elle gère également le traitement de la transcription reçue.
    """
    def __init__(self, host: str, port: int, lang: str, translate: bool, use_vad: bool,
                 save_output_recording: bool, output_recording_filename: str,
                 update_callback, insertions, fenetre_gestion_insertions,
                 mode, nb_repeat: int = 2, ip_client: str = "0.0.0.0", listen: bool = False) -> None:
        """
        Initialise un gestionnaire de client.

        Args:
            host (str): Adresse IP ou nom d'hôte du serveur.
            port (int): Port de communication WebSocket.
            lang (str): Langue cible pour la transcription.
            translate (bool): Active la traduction si True.
            use_vad (bool): Active la détection de voix si True.
            save_output_recording (bool): Enregistre localement l'audio si True.
            output_recording_filename (str): Chemin du fichier de sortie.
            update_callback (callable): Fonction de callback pour mettre à jour l'interface.
            insertions: Gestionnaire des insertions personnalisées.
            fenetre_gestion_insertions: Fonction qui retourne True si l'on est dans la gestion des insertions.
            mode: Mode d'exécution (ex: DIRECT, APPRENTI, REDUIT).
            nb_repeat (int): Nombre de répétitions avant de considérer une phrase comme terminée.
            ip_client (str): IP du client à transmettre au serveur.
            listen (bool): Active l'écoute locale de l'audio si True.
        """
        self.host = host
        self.port = port
        self.lang = lang
        self.model = None
        self.translate = translate
        self.use_vad = use_vad
        self.save_output_recording = save_output_recording
        self.output_recording_filename = output_recording_filename
        self.client = None
        self.running = False
        self.client_thread = None
        self.loop = None
        self.update_callback = update_callback
        self.insertions = insertions
        self.fenetre_gestion_insertions = fenetre_gestion_insertions
        self.mode = mode.mode  # Direct, Reduit etc...
        self._mode = mode  # TODO: à simplifier !!
        self.nb_repeat = nb_repeat
        self.last_partial_text = ""
        self.ip_client = ip_client
        self.listen = listen

    def start_client(self, loop, port_service=None, audio_file=None, listen=False) -> None:
        """
        Démarre une nouvelle instance de Client dans un thread séparé.

        Args:
            loop: Boucle asyncio utilisée par le client.
            port_service (int | None): Port alternatif si différent de self.port.
            audio_file (str | None): Chemin d'un fichier audio à lire au lieu du micro.
            listen (bool): Si True, joue l'audio localement aussi.
        """
        port = port_service
        if port is None:
            port = self.port
        print(f"Starting client in ClientManager in [{port}]")
        self.stop_client()  # Ensure any previous client is stopped before starting a new one

        self.client = Client(
            host=self.host,
            port=port,
            lang=self.lang,
            model=self.model,
            translate=self.translate,
            use_vad=self.use_vad,
            save_output_recording=self.save_output_recording,
            output_recording_filename=self.output_recording_filename,
            call_back=self.call_back,
            nb_repeat=self.nb_repeat,
            ip_client=self.ip_client
        )
        self.audio_file = audio_file
        self.listen = listen
        self.client.set_pause(False)
        self.running = True
        self.loop = loop
        # Run the client in a separate thread to avoid blocking the event loop
        self.client_thread = threading.Thread(target=self.run_client_thread)
        self.client_thread.start()

    def run_client_thread(self) -> None:
        """
        Fonction exécutée dans un thread. Gère la lecture du fichier audio ou l'enregistrement
        micro et gère les erreurs si le serveur ne répond pas.
        """
        try:
            # ⏳ Attente active de la WebSocket READY
            if not self.client.ready_event.wait(timeout=5):  # max 5 secondes
                print("[ERROR] Le serveur n'a pas répondu à temps.")
                self.stop_client()
                self._mode.stop_client()
                return

            if self.audio_file:
                self.client.source_is_micro = False
                self.client.play_file(self.audio_file, listen=self.listen)
            else:
                self.client.source_is_micro = True
                self.model = self.client.get_model_path()
                self.client.record()

            self.client = None
        except Exception as e:
            print("Traceback complet :")
            traceback.print_exc()

            if isinstance(e, (EOFError, wave.Error)):
                messagebox.showerror(
                    "Fichier audio invalide",
                    f"Le fichier ne peut pas être lu comme un fichier audio valide.\n\n"
                    f"Fichier :\n{self.audio_file}\n\nErreur :\n{e}"
                )
            else:
                print(f"Erreur dans run_client :{repr(e)}")

            self.stop_client()
            self._mode.stop_client()  # on stop le client appelant

    def call_back(self, texte: str, ending: bool, force: bool = False) -> None:
        """
        Fonction appelée par le client lorsqu'une transcription est reçue.

        Args:
            texte (str): Le texte transcrit.
            ending (bool): True si la phrase est terminée.
            force (bool): Si True, force l'arrêt même sans audio_file.
        """
        if texte is None:  # appel du call back suite à ending=True
            # print(f"*************ici self._mode.app.recording = {self._mode.app.recording}")
            if self.audio_file is not None or force:
                self._mode.app.recording = False
                self.update_callback(None, True)
            return

        combined_text = texte.lstrip()

        if not (self.fenetre_gestion_insertions() or self.mode == APPRENTI):
            combined_text = intercept(combined_text, self.insertions.get())
            if self.mode != APPRENTI:
                combined_text = corrige_ponctuation(combined_text)

        if combined_text != "":
            # On ne fait pas de correction si on est en mode APPRENTI
            if not self.fenetre_gestion_insertions():
                self.update_callback(combined_text, ending)
            else:
                if ending:
                    Simulator(combined_text)

    def stop_client(self) -> None:
        """
        Stoppe proprement le client et attend la fin du thread associé.
        """
        self.running = False
        if self.client:
            try:
                self.client.stop()
            except Exception as e:
                print(f"[ERROR] lors de l'arrêt du client : {e}")
            self.client = None

        # Attendre la fin du thread si on n'est pas déjà dedans
        if self.client_thread is not None:
            if threading.current_thread() != self.client_thread:
                self.client_thread.join()
            self.client_thread = None

    def pause(self) -> None:
        """
        Met le client en pause si celui-ci est actif.
        """
        if self.client:
            self.client.set_pause(True)
            self.client.send_end_of_audio_signal()
