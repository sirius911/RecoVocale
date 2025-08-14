import json
import os
import pywinusb.hid as hid
import asyncio
from Actions import (  # noqa: F401
    Action, NoAction, Pause, Unpause, ValidTranscriptions, StopAction,
    Clear, Toggle_start_stop, Keyboard, Copie_clipboard, CopierColler, Attendre, Run
)
from typing import Optional, Callable

from utils_window import resource_path, get_config_path


def hash_code(data: list[int]) -> int:
    """
    Calcule un code de hachage à partir des deux derniers octets de `data`.
    Utilisé pour les micros de première génération.
    On pourra prendre le hash_code2 en mettant à jour le fichier de configuration micro_actions_config.json

    Args:
        data (list[int]): Données brutes reçues du micro.

    Returns:
        int: Code de hachage calculé.

    Raises:
        ValueError: Si `data` a une longueur inférieure à 2.
    """
    if len(data) < 2:
        raise ValueError(f"Bad hash_code: {data}")

    avant_dernier = data[-2]
    dernier = data[-1]
    hash_code = avant_dernier*256 + dernier
    return hash_code


def hash_code2(data: list[int]) -> int:
    """
    Calcule un code de hachage basé sur la somme pondérée des octets.

    Args:
        data (list[int]): Données brutes reçues du micro.

    Returns:
        int: Code de hachage calculé.
    """
    result = 0
    for i, val in enumerate(data):
        result += val * (i + 1)
    return result


class BaseMic:
    """
    Classe représentant un microphone HID avec prise en charge des actions personnalisées.

    Cette classe détecte les connexions/déconnexions du micro, gère les données HID reçues
    et déclenche dynamiquement les actions associées définies dans un fichier de configuration.
    """

    def __init__(self, loop, vendor_id, product_id, firmware, actions,
                 app, micro_name, on_connect_disconnect=None, hash=1,
                 interfaces: "list[str] | str | None" = None):
        """
        Initialise le micro HID avec ses paramètres et démarre la surveillance asynchrone.

        Args:
            loop: Boucle asyncio dans laquelle exécuter les tâches.
            vendor_id (int): ID du fabricant USB.
            product_id (int): ID du produit USB.
            firmware (int): Version du firmware du micro.
            actions (dict): Dictionnaire de hash → actions à exécuter.
            app: Référence à l'application principale.
            micro_name (str): Nom logique du micro (utilisé pour affichage).
            on_connect_disconnect (callable | None): Callback appelé lors des changements de connexion.
            hash (int): Méthode de hachage à utiliser (1 pour `hash_code`, 2 pour `hash_code2`).
        """

        self.vendor_id = vendor_id
        self.product_id = product_id
        self.version = firmware
        self.actions = actions
        self.app = app
        self.loop = loop
        self.micro_name = micro_name
        self.connected = False
        self.device = []
        self.interface_filters = interfaces
        self.prev_data = None
        self.call_back = on_connect_disconnect
        # Choix de la fonction de hash selon le modèle
        if hash == 2:
            self.hash_function = hash_code2  # nouvelle méthode
        else:
            self.hash_function = hash_code   # méthode legacy

        # Démarre la coroutine monitor dans une tâche
        asyncio.run_coroutine_threadsafe(self.monitor(), self.loop)

    async def check_connection(self) -> None:
        """
        Vérifie si le micro est connecté, et appelle `connect` ou `disconnect` en conséquence.
        """

        if self.version != 0:
            all_hids = hid.HidDeviceFilter(
                vendor_id=self.vendor_id,
                product_id=self.product_id,
                version_number=self.version
            ).get_devices()
        else:
            all_hids = hid.HidDeviceFilter(
                vendor_id=self.vendor_id,
                product_id=self.product_id
            ).get_devices()

        if all_hids:
            if not self.connected:
                self.devices = all_hids  # ← stocke toutes les interfaces
                self.connected = True
                self.connect()
        else:
            if self.connected:
                self.devices = []
                self.connected = False
                self.disconnect()
                print(f"{self.__class__.__name__} non trouvé. En attente de connexion...")

        self.call_back()

    def connect(self) -> None:
        """
        Ouvre les interfaces HID disponibles et associe un gestionnaire de données à chaque interface.
        """

        if self.connected:
            self.devices = hid.HidDeviceFilter(
                vendor_id=self.vendor_id,
                product_id=self.product_id
            ).get_devices()

            # Filtrage éventuel par "colXX"
            def _col_name(dev):
                try:
                    return "col" + dev.device_path.lower().split("col")[-1].split("#")[0]
                except Exception:
                    return None

            if self.interface_filters and self.interface_filters != "all":
                wanted = {c.lower() for c in self.interface_filters}
                self.devices = [d for d in self.devices if (_col_name(d) or "").lower() in wanted]
            # print(f"self.devices = {self.devices}")
            for dev in self.devices:
                try:
                    dev.open()
                    dev.set_raw_data_handler(self.on_data_handler)
                    col_name = "col" + dev.device_path.lower().split("col")[-1].split("#")[0]
                    print(f"{self.micro_name} → Interface HID activée : {dev.product_name} | " +
                          f"Serial: {dev.serial_number or 'N/A'} | Interface: {col_name}")

                except Exception as e:
                    print(f"Erreur ouverture interface : {e}")

    def disconnect(self) -> None:
        """
        Ferme toutes les interfaces HID ouvertes et nettoie la liste des périphériques.
        """

        for dev in self.devices:
            try:
                dev.close()
            except Exception:
                pass
        self.devices = []

    def is_connected(self) -> bool:
        """
        Indique si le micro est actuellement connecté.

        Returns:
            bool: True si connecté, False sinon.
        """

        return self.connected

    def change_mode(self, mode) -> None:
        """
        Change l'objet `app` pour rediriger les actions du micro vers un nouveau mode.

        Args:
            mode: Instance de mode (`Mode_Direct`, `Mode_Apprenti`, etc.)
        """

        self.app = mode

    def on_data_handler(self, data: list[int]) -> None:
        """
        Appelé automatiquement lorsqu'une nouvelle donnée HID est reçue.

        Args:
            data (list[int]): Tableau de données HID.
        """

        if data != self.prev_data:
            self.prev_data = data
            self.handle_data(data)

    def handle_data(self, data: list[int]) -> None:
        """
        Traite les données HID et déclenche l'action associée si un code de hachage est reconnu.

        Args:
            data (list[int]): Tableau de données brutes du micro.
        """

        hashcode = str(self.hash_function(data))

        if hashcode in self.actions:
            # print(f"hascode = {hashcode} ... trouvé")
            action_info = self.actions[hashcode]
            action_class = action_info["class"]
            # Instancier dynamiquement la classe d'action
            ActionClass = globals().get(action_class)
            if ActionClass:
                action = ActionClass(self.app)
                # print(f"Execution de {action.__name__}")
                if action.__name__ == 'NoAction':
                    action.execute(hashcode)
                # Vérifier si l'action a un argument
                elif "arg" in action_info:
                    action.execute(action_info["arg"])
                else:
                    action.execute()
            else:
                print(f"Classe d'action {action_class} introuvable pour {str(data)} ({hashcode})")
        else:
            print(f"No action found for data: {str(data)} {self.hash_function.__name__} ({hashcode})")

    async def monitor(self) -> None:
        """
        Coroutine qui vérifie en boucle la connexion du micro toutes les 5 secondes.
        """

        while True:
            await self.check_connection()
            await asyncio.sleep(5)


def Micro(
    loop: asyncio.AbstractEventLoop,
    app: object,
    call_back: Callable[[], None]
) -> Optional[BaseMic]:
    """
    Initialise et retourne une instance de `BaseMic` si un micro compatible est détecté.

    Lit la configuration JSON des micros autorisés et leur associe les actions définies.

    Args:
        loop: Boucle asyncio utilisée pour la surveillance du micro.
        app: Instance de l'application qui exécutera les actions.
        call_back: Fonction appelée lors des événements de connexion/déconnexion.

    Returns:
        BaseMic | None: Instance de BaseMic si un micro est trouvé, sinon None.
    """

    # Charger le fichier JSON depuis le répertoire utilisateur
    config_path = get_config_path("micro_actions_config.json")
    # Vérifier si le fichier de config existe dans %APPDATA%, sinon le copier depuis le package
    if not os.path.exists(config_path):
        default_config_path = resource_path("config/micro_actions_config.json")
        print(f"Tentative de copie de la configuration par défaut depuis : {default_config_path}")
        try:
            with open(default_config_path, "r") as default_file:
                with open(config_path, "w") as config_file:
                    config_file.write(default_file.read())
            print(f"Fichier de configuration copié dans {config_path}")
        except FileNotFoundError:
            print(f"Le fichier de configuration par défaut est introuvable : {default_config_path}")
            raise
    print(f"lecture du fichier de configuration : {config_path}")
    with open(config_path, "r") as file:
        config = json.load(file)
    for micro_name, micro_info in config.items():
        # Convertir les vendor_id, product_id et firmwarehexadécimaux en entiers
        try:
            vendor_id = int(micro_info["vendor_id"], 16)
            product_id = int(micro_info["product_id"], 16)
            firmware_revision = int(micro_info["firmware"], 16)
            actions = micro_info["actions"]
            hash_value = int(micro_info.get("hash", "0x01"), 16)
            interfaces = micro_info.get("interfaces")  # None / "all" / ["col01", ...]

        except Exception as e:
            print(f"Erreur dans la lecture du fichier [{file}]\n{e}\n Il faut mettre à jour le fichier json !")
            return None

        if firmware_revision > 0:
            # si pas de firmware c'est que l'on prend le speech Mike generique
            all_hids = hid.HidDeviceFilter(vendor_id=vendor_id, product_id=product_id,
                                           version_number=firmware_revision).get_devices()
        else:
            all_hids = hid.HidDeviceFilter(vendor_id=vendor_id, product_id=product_id).get_devices()

        if all_hids:
            temp_mic = BaseMic(loop, vendor_id, product_id, firmware_revision,
                               actions, app, micro_name, call_back, hash=hash_value, interfaces=interfaces)
            return temp_mic  # Retourne l'instance de la classe détectée
        else:
            print(f"{micro_name} ... non trouvé")

    return None  # Aucun micro compatible trouvé
