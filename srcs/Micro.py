import json
import os
import pywinusb.hid as hid
import asyncio
from Actions import *
from utils_window import resource_path, get_config_path

class BaseMic:
    def __init__(self, loop, vendor_id, product_id, actions, app, micro_name):
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.actions = actions
        self.app = app
        self.loop = loop
        self.micro_name = micro_name  
        self.connected = False
        self.device = None
        self.prev_data = None

        # Démarre la coroutine monitor dans une tâche
        asyncio.run_coroutine_threadsafe(self.monitor(), self.loop)

    async def check_connection(self):
        all_hids = hid.HidDeviceFilter(vendor_id=self.vendor_id, product_id=self.product_id).get_devices()
        if all_hids:
            if not self.connected:
                self.device = all_hids[0]
                self.connected = True
                self.connect()
        else:
            if self.connected:
                self.device = None
                self.connected = False
                self.disconnect()
                print(f"{self.__class__.__name__} non trouvé. En attente de connexion...")

    def connect(self):
        if self.connected and self.device:
            self.device.open()
            self.device.set_raw_data_handler(self.on_data_handler)
            print(f"{self.micro_name} connecté")

    def disconnect(self):
        if self.device:
            self.device.close()
            self.connected = False
            print(f"{self.micro_name} déconnecté")

    def on_data_handler(self, data):
        if data != self.prev_data:
            self.prev_data = data
            self.handle_data(data)

    def handle_data(self, data):
        data_str = str(data)
        if data_str in self.actions:
            action_info = self.actions[data_str]
            action_class = action_info["class"]
            
            # Instancier dynamiquement la classe d'action
            ActionClass = globals().get(action_class)
            if ActionClass:
                action = ActionClass(self.app)
                # Vérifier si l'action a un argument
                if "arg" in action_info:
                    action.execute(action_info["arg"])
                else:
                    action.execute()
            else:
                print(f"Classe d'action {action_class} introuvable pour {data_str}")
        else:
            print(f"No action found for data: {data_str}")

    async def monitor(self):
        while True:
            await self.check_connection()
            await asyncio.sleep(1)

def Micro(loop, app):
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
    with open(config_path, "r") as file:
        config = json.load(file)
    for micro_name, micro_info in config.items():
        # Convertir les vendor_id et product_id hexadécimaux en entiers
        vendor_id = int(micro_info["vendor_id"], 16)
        product_id = int(micro_info["product_id"], 16)
        actions = micro_info["actions"]

        temp_mic = BaseMic(loop, vendor_id, product_id, actions, app, micro_name)
        all_hids = hid.HidDeviceFilter(vendor_id=vendor_id, product_id=product_id).get_devices()
        if all_hids:
            return temp_mic  # Retourne l'instance de la classe détectée

    return None  # Aucun micro compatible trouvé
