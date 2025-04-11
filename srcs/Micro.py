import json
import os
import pywinusb.hid as hid
import asyncio
from Actions import *
from utils_window import resource_path, get_config_path

def hash_code(data):
    # Pour les Micro 1ere génération
    # On pourra prendre le hash_code2 en mettant à jour le fichier de configuration micro_actions_config.json
    if len(data) < 2:
        raise ValueError(f"Bad hash_code: {data}")
    
    avant_dernier = data[-2]
    dernier = data[-1]
    hash_code = avant_dernier*256 + dernier
    return hash_code

def hash_code2(data):
    result = 0
    for i, val in enumerate(data):
        result += val * (i + 1)
    return result

class BaseMic:
    def __init__(self, loop, vendor_id, product_id, firmware, actions, app, micro_name, on_connect_disconnect=None):
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.version = firmware
        self.actions = actions
        self.app = app
        self.loop = loop
        self.micro_name = micro_name  
        self.connected = False
        self.device = None
        self.prev_data = None
        self.call_back = on_connect_disconnect
        # Choix de la fonction de hash selon le modèle
        if "Premium" in micro_name or self.version == 0x0253:
            self.hash_function = hash_code2  # nouvelle méthode
        else:
            self.hash_function = hash_code   # méthode legacy


        # Démarre la coroutine monitor dans une tâche
        asyncio.run_coroutine_threadsafe(self.monitor(), self.loop)

    async def check_connection(self):
        # all_hids = hid.HidDeviceFilter(vendor_id=self.vendor_id, product_id=self.product_id, version_number=self.version).get_devices()
        if self.version:
            all_hids = hid.HidDeviceFilter(vendor_id=self.vendor_id, product_id=self.product_id, version_number=self.version).get_devices()
        else:
            all_hids = hid.HidDeviceFilter(vendor_id=self.vendor_id, product_id=self.product_id).get_devices()

        if all_hids:
            if not self.connected:
                # Si Premium, on cherche l'interface MI_04
                if "Premium" in self.micro_name:
                    for dev in all_hids:
                        if "mi_04" in dev.device_path.lower():
                            self.device = dev
                            break
                else:
                    self.device = all_hids[0]

                if self.device:
                    self.connected = True
                    self.connect()
                else:
                    print(f"Aucun device MI_04 trouvé pour {self.micro_name}")
        else:
            if self.connected:
                self.device = None
                self.connected = False
                self.disconnect()
                print(f"{self.__class__.__name__} non trouvé. En attente de connexion...")
        self.call_back()

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

    def is_connected(self):
        return self.connected

    def change_mode(self, mode):
        self.app = mode

    def on_data_handler(self, data):
        if data != self.prev_data:
            self.prev_data = data
            self.handle_data(data)

    def handle_data(self, data):
        hascode = str(self.hash_function(data))

        if hascode in self.actions:
            
            action_info = self.actions[hascode]
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
                print(f"Classe d'action {action_class} introuvable pour {str(data)} ({hascode})")
        else:
            print(f"No action found for data: {str(data)} ({hascode})")

    async def monitor(self):
        while True:
            await self.check_connection()
            await asyncio.sleep(5)

def Micro(loop, app, call_back):
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
        except Exception as e:
            print(f"Erreur dans la lecture du fichier [{file}]\n{e}\n Il faut mettre à jour le fichier json !")
            return None
        temp_mic = BaseMic(loop, vendor_id, product_id, firmware_revision, actions, app, micro_name, call_back)
        all_hids = hid.HidDeviceFilter(vendor_id=vendor_id, product_id=product_id, version_number=firmware_revision).get_devices()
        # all_hids = hid.HidDeviceFilter(vendor_id=vendor_id, product_id=product_id).get_devices()
        if all_hids:
            return temp_mic  # Retourne l'instance de la classe détectée

    return None  # Aucun micro compatible trouvé
