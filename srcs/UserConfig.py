import os
import configparser


class UserConfig:
    """
    Gère la configuration utilisateur de l'application RecoVocale.

    Cette classe charge, sauvegarde et expose les paramètres de configuration stockés
    dans un fichier `user_config.ini` dans `%APPDATA%/RecoVocale`.

    Elle prend en charge :
    - les ports et adresses du serveur,
    - les raccourcis clavier,
    - le mode de démarrage,
    - la position de la fenêtre,
    - les options de transcription.

    Les attributs sont exposés via des propriétés pour permettre une validation et
    un comportement dynamique (ex : changer de port selon le service).
    """

    def __init__(self):
        """
        Initialise la configuration utilisateur :
        - définit les valeurs par défaut,
        - crée ou charge le fichier `user_config.ini`.
        """

        # Définir le chemin du répertoire de configuration dans %APPDATA%\RecoVocale
        self.config_dir = os.path.join(os.getenv('APPDATA'), 'RecoVocale')
        self.config_file = os.path.join(self.config_dir, "user_config.ini")
        print(f"init avec {self.config_file}")
        # Valeurs par défaut
        self.server_ip = "10.1.147.251"
        self.tensorRT_ip = "10.1.147.252"
        self.faster_ip = "10.1.147.251"
        self._port = "30000"
        self._service = "Tous"
        self._shortcut = "F3"
        self._shortcut_stop = "F4"
        self._play_audio = True
        self.mode = "DIRECT"
        self.x_window = "10"
        self.y_window = "10"
        self.debug = False
        self.insertions = "insertions.xml"
        self.nb_repeat = 3
        self.dictionnaire = False
        self._service_port_map = {
            "Tous": "30000",
            "Général": "30001",
            "Radiologie": "30002",
            "Cardiologie": "30003",
            "Oncologie": "30004",
            "Model RT": "30000"
        }
        self._word_space = False

        # Lire la configuration si le fichier existe, sinon la créer
        if os.path.exists(self.config_file):
            self.load_config()
        else:
            self.save_config(None)

    def load_config(self) -> None:
        """
        Charge la configuration depuis le fichier `user_config.ini`.
        Utilise des valeurs par défaut si des champs sont manquants.
        """

        config = configparser.ConfigParser()
        config.read(self.config_file)

        self.server_ip = config.get('SETTINGS', 'SERVEUR_IP', fallback=self.server_ip)
        self.tensorRT_ip = config.get('SETTINGS', 'TENSORRT_IP', fallback=self.tensorRT_ip)
        self._port = config.get('SETTINGS', 'PORT', fallback=self._port)
        self._service = config.get('SETTINGS', 'SERVICE', fallback=self._service)
        self._shortcut = config.get('SETTINGS', 'SHORTCUT', fallback=self._shortcut)
        if self._shortcut is None or self._shortcut == "":
            self._shortcut = "F3"
        self._shortcut_stop = config.get('SETTINGS', 'SHORTCUT_STOP', fallback=self._shortcut_stop)
        if self._shortcut_stop is None or self._shortcut_stop == "":
            self._shortcut_stop = "F4"
        self.mode = config.get('SETTINGS', 'MODE', fallback=self.mode)
        self.x_window = config.get('SETTINGS', 'X_WINDOW', fallback=self.x_window)
        self.y_window = config.get('SETTINGS', 'Y_WINDOW', fallback=self.y_window)
        self.debug = (config.get('SETTINGS', 'DEBUG', fallback=self.debug) == 'True')
        self.insertions = config.get('SETTINGS', 'INSERTIONS', fallback=self.insertions)
        self.nb_repeat = int(config.get('SETTINGS', 'NB_REPEAT', fallback=self.nb_repeat))
        self.dictionnaire = (config.get('SETTINGS', 'DICTIONNAIRE', fallback=self.dictionnaire) == 'True')
        self._play_audio = (config.get('SETTINGS', 'PLAY_AUDIO', fallback=self._play_audio) == 'True')
        self._word_space = (config.get('SETTINGS', 'WORD_SPACE', fallback=self._word_space) == 'True')

    def save_config(self, root) -> None:
        """
        Sauvegarde la configuration actuelle dans `user_config.ini`.

        Args:
            root: Fenêtre Tkinter (utilisée pour enregistrer la position de la fenêtre).
        """

        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)

        config = configparser.ConfigParser()
        config['SETTINGS'] = {
            'SERVEUR_IP': self.server_ip,
            'TENSORRT_IP': self.tensorRT_ip,
            'PORT': self._port,
            'SERVICE': self._service,
            'SHORTCUT': self._shortcut,
            'SHORTCUT_STOP': self._shortcut_stop,
            'MODE': self.mode,
            'X_WINDOW': root.winfo_x() if root else 0,
            'Y_WINDOW': root.winfo_y() if root else 0,
            'DEBUG': 'True' if self.debug else 'False',
            'INSERTIONS': self.insertions,
            'NB_REPEAT': self.nb_repeat,
            'DICTIONNAIRE': self.dictionnaire,
            'PLAY_AUDIO': self._play_audio,
            'WORD_SPACE': self._word_space,
        }
        print(f"Sauvegarde {self.config_file} ...", end=' ')

        with open(self.config_file, 'w') as configfile:
            config.write(configfile)
        print("Ok")

    def get_services(self) -> list[str]:
        """
        Retourne la liste des services disponibles dans la configuration.

        Returns:
            list[str]: Liste des noms de service configurés.
        """

        return list(self._service_port_map.keys())

    @property
    def port(self) -> str:
        """Retourne le port utilisé actuellement."""

        return self._port

    @port.setter
    def port(self, value: str) -> None:
        """Définit manuellement un nouveau port."""
        self._port = value

    @property
    def service(self) -> str:
        """Retourne le nom du service sélectionné."""
        return self._service

    @service.setter
    def service(self, value: str) -> None:
        """
        Définit un nouveau service et adapte automatiquement le port correspondant
        s'il est connu.

        Args:
            value (str): Nom du service à activer.
        """
        self._service = value
        if value in self._service_port_map:
            self._port = self._service_port_map[value]
            if value == "Model RT":
                self.server_ip = self.tensorRT_ip
            else:
                self.server_ip = self.faster_ip
            print(f"{self.server_ip} : changement de Port : {self._port}")

    @property
    def play_audio(self) -> bool:
        """Retourne l'état de l'option 'play_audio'."""
        return self._play_audio

    @play_audio.setter
    def play_audio(self, value: bool) -> None:
        """Active ou désactive l'écoute locale de l'audio."""
        self._play_audio = value

    @property
    def shortcut(self) -> str:
        """Retourne le raccourci clavier principal."""
        return self._shortcut

    @shortcut.setter
    def shortcut(self, value: str) -> None:
        """Définit le raccourci clavier principal."""
        self._shortcut = value

    @property
    def shortcut_stop(self) -> str:
        """Retourne le raccourci pour arrêter la transcription."""
        return self._shortcut_stop

    @shortcut_stop.setter
    def shortcut_stop(self, value: str) -> None:
        """Définit le raccourci pour arrêter la transcription."""
        self._shortcut_stop = value

    @property
    def word_space(self) -> bool:
        """Retourne l'état de l'option 'word_space'."""
        return self._word_space

    @word_space.setter
    def word_space(self, value: bool) -> None:
        """Active ou désactive l'espace apres chaque segment en mode réduit."""
        self._word_space = value
