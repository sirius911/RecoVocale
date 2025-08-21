import collections
import json
import os
import pywinusb.hid as hid
import asyncio
from Actions import (  # noqa: F401
    Action, NoAction, Pause, Unpause, ValidTranscriptions, StopAction,
    Clear, Toggle_start_stop, Keyboard, Copie_clipboard, CopierColler, Attendre, Run
)
from typing import Optional, Callable
import time
from utils_window import resource_path, get_config_path
from queue_manager import UI_QUEUE


OPENED_HID_PATHS: set[str] = set()


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
                 interfaces: "list[str] | str | None" = None,
                 settle_ms: int = 1500,
                 required_prefix: "list[int] | list[list[int]] | None" = None):

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
        self.devices = []
        self.interface_filters = interfaces
        self.prev_data = None
        self.call_back = on_connect_disconnect
        self._opened_paths: list[str] = []

        # ---- anti-bruit de reconnexion ----
        self.required_prefix = required_prefix      # ex: [0,129] ; None = pas de filtre
        self.settle_ms = int(settle_ms)          # durée d’attente après (re)connexion
        self._settle_until = 0.0                 # timestamp (monotonic) fin d’attente

        # --- Détection de rafale HID (reprise/initialisation) ---
        self.resume_burst_window_ms = 500     # élargit un peu la fenêtre
        self.resume_burst_min_frames = 4      # seuil total plus bas
        self.resume_burst_codes = {6, 7, 5, 4, 1, 3, 14, 15, 10, 11, 12, 255, 85, 3200, 13113, 83, 0, 8}
        self.resume_quick_pair_ms = 80        # ⚠️ nouveau : 2 suspects ≤ 80ms => settle immédiat
        self._burst_times = collections.deque(maxlen=64)
        self._last_suspect_ts = 0.0           # ⚠️ nouveau

        # Choix de la fonction de hash selon le modèle
        if hash == 2:
            self.hash_function = hash_code2  # nouvelle méthode
        else:
            self.hash_function = hash_code   # méthode legacy

        # Démarre la coroutine monitor dans une tâche
        asyncio.run_coroutine_threadsafe(self.monitor(), self.loop)

    def _maybe_resume_burst(self, int_code: int, now: float) -> bool:
        """
        Détecte une rafale HID (reprise/réinit). Retourne True si on arme settle
        et qu'on doit ignorer la trame courante.
        Règles:
        - si 2 trames 'suspectes' arrivent à <= resume_quick_pair_ms -> settle immédiat
        - sinon, si >= resume_burst_min_frames trames dans resume_burst_window_ms -> settle
        - si trame 'saine' (non suspecte), on purge le tampon (sortie du mode rafale).
        """
        # 1) 'suspect' = code de la liste OU code inconnu (non mappé)
        suspect = (int_code in self.resume_burst_codes) or (str(int_code) not in self.actions)

        if suspect:
            # (a) Quick-pair: 2 suspects très rapprochés => settle immédiat
            if self._last_suspect_ts and ((now - self._last_suspect_ts) * 1000.0 <= self.resume_quick_pair_ms):
                self._settle_until = time.monotonic() + (self.settle_ms / 1000.0)
                self.prev_data = None
                self._burst_times.clear()
                self._last_suspect_ts = 0.0
                print(f"{self.micro_name} → rafale HID détectée (pair), stabilisation ~{self.settle_ms} ms")
                return True

            # (b) Sinon on accumule dans la fenêtre
            self._last_suspect_ts = now
            self._burst_times.append(now)

            win_start = now - (self.resume_burst_window_ms / 1000.0)
            # compte rapide dans la fenêtre
            n = 0
            for t in reversed(self._burst_times):
                if t < win_start:
                    break
                n += 1

            if n >= self.resume_burst_min_frames:
                self._settle_until = time.monotonic() + (self.settle_ms / 1000.0)
                self.prev_data = None
                self._burst_times.clear()
                self._last_suspect_ts = 0.0
                print(f"{self.micro_name} → rafale HID détectée, stabilisation ~{self.settle_ms} ms")
                return True

            # sinon, on reste en observation (on ne bloque pas encore)
            return False

        # 2) Trame 'saine' → on sort du mode rafale
        self._burst_times.clear()
        self._last_suspect_ts = 0.0
        return False

    def _safe_ui(self, fn: Callable[[], None]) -> None:
        """Poste une fonction UI dans la file pour exécution dans le thread Tk."""
        try:
            UI_QUEUE.put(fn)
        except Exception:
            pass

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
                if self.call_back:
                    self._safe_ui(self.call_back)
        else:
            if self.connected:
                self.devices = []
                self.connected = False
                self.disconnect()
                print(f"{self.__class__.__name__} non trouvé. En attente de connexion...")
                if self.call_back:
                    self._safe_ui(self.call_back)

    def connect(self) -> None:
        """
        Ouvre les interfaces HID disponibles et associe un gestionnaire de données à chaque interface.
        """
        # Fenêtre d’attente après (re)connexion
        now = time.monotonic()
        self._settle_until = now + (self.settle_ms / 1000.0)
        self.prev_data = None
        print(f"{self.micro_name} → initialisation du micro… (~{self.settle_ms} ms)")

        if self.connected:
            devices = self.devices or hid.HidDeviceFilter(
                vendor_id=self.vendor_id,
                product_id=self.product_id
            ).get_devices()
            self.devices = devices

            # Filtrage éventuel par "colXX"
            def _col_name(dev):
                try:
                    path = (dev.device_path or "").lower()
                    if "col" in path:
                        return "col" + path.split("col")[-1].split("#")[0]
                    return "root"
                except Exception:
                    return "root"

            if self.interface_filters and self.interface_filters != "all":
                wanted = {c.lower() for c in self.interface_filters}
                self.devices = [d for d in self.devices if (_col_name(d) or "").lower() in wanted]

            for dev in self.devices:
                self.prev_data = None

                # --- verrou global pour éviter les doublons d’ouverture ---
                path = getattr(dev, "device_path", "") or ""
                norm_path = path.lower()
                if norm_path and norm_path in OPENED_HID_PATHS:
                    # Déjà ouverte par un autre watcher → on la saute
                    # (facultatif) décommente si tu veux voir quand ça arrive :
                    print(f"{self.micro_name} → interface déjà ouverte ailleurs, on saute: {norm_path}")
                    continue

                try:
                    try:
                        dev.open(shared=True)
                    except TypeError:
                        dev.open()

                    dev.set_raw_data_handler(self.on_data_handler)

                    if norm_path:
                        OPENED_HID_PATHS.add(norm_path)
                        self._opened_paths.append(norm_path)

                    col_name = _col_name(dev)
                    print(f"{self.micro_name} → Interface HID activée : {dev.product_name} | "
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
        self.prev_data = None

        # Libère les chemins ouverts par CE watcher
        for p in self._opened_paths:
            try:
                OPENED_HID_PATHS.discard(p)
            except Exception:
                pass
        self._opened_paths.clear()

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
        # 1) Pendant la fenêtre d’attente “settle”, on ignore absolument tout (zéro action, zéro log)
        if time.monotonic() < self._settle_until:
            return

        # 2) Filtre par préfixe (accepte 1 ou N préfixes)
        if self.required_prefix:
            prefixes = self.required_prefix
            if isinstance(prefixes, list) and prefixes and isinstance(prefixes[0], int):
                prefixes = [prefixes]  # normalise: [0,129] -> [[0,129]]
            if not any(len(data) >= len(pref) and data[:len(pref)] == pref for pref in prefixes):
                return

        # 3) Anti-duplication brute
        if data == self.prev_data:
            return
        self.prev_data = data

        # 4) -> DÉTECTION DE RAFALE HID
        try:
            int_code = self.hash_function(data)
        except Exception:
            return
        if self._maybe_resume_burst(int_code, time.monotonic()):
            return  # on vient d’armer settle : on ne traite pas cette trame

        # 5) Envoi au résolveur d'actions
        self.handle_data(data)

    def handle_data(self, data: list[int]) -> None:
        # Si on est encore en "settle", on ne loggue rien et on ne déclenche rien
        if time.monotonic() < getattr(self, "_settle_until", 0.0):
            return

        # hash en INT pour la logique
        try:
            int_code = self.hash_function(data)
        except Exception:
            return

        # lookup en STR dans le mapping JSON
        action_info = self.actions.get(str(int_code))
        if not action_info:
            # (option) commenter pour silence total :
            print(f"No action found for data: {data} hash_code ({int_code})")
            return

        action_class = action_info.get("class")
        ActionClass = globals().get(action_class)
        if not ActionClass:
            # print(f"Classe d'action {action_class} introuvable pour {str(data)} ({int_code})")
            return

        action = ActionClass(self.app)
        print(f"[{int_code}]-Execution de {ActionClass.__name__}")
        if ActionClass.__name__ == 'NoAction':
            action.execute(int_code)
        elif "arg" in action_info:
            action.execute(action_info["arg"])
        else:
            action.execute()

    async def monitor(self) -> None:
        """
        Coroutine qui vérifie en boucle la connexion du micro toutes les 5 secondes.
        """

        while True:
            try:
                await self.check_connection()
            except Exception as e:
                print(f"[monitor] erreur: {e}")
            await asyncio.sleep(1 if not self.connected else 5)


class MultiMic:
    def __init__(self, mics: list[BaseMic]):
        self.mics = mics

    def is_connected(self) -> bool:
        return any(m.is_connected() for m in self.mics)

    def change_mode(self, mode) -> None:
        for m in self.mics:
            m.change_mode(mode)

    def disconnect(self) -> None:
        for m in self.mics:
            try:
                m.disconnect()
            except Exception:
                pass

    @property
    def micro_name(self) -> str:
        connected = [m.micro_name for m in self.mics if m.is_connected()]
        return connected[0] if connected else "Aucun"


def Micro(
    loop: asyncio.AbstractEventLoop,
    app: object,
    call_back: Callable[[], None]
) -> Optional[BaseMic]:
    """
    Crée UN watcher par entrée de config (spécifique ET/OU générique).
    Si plusieurs watchers sont créés, on retourne un MultiMic qui les agrège.
    """

    # Charger le fichier JSON depuis le répertoire utilisateur
    config_path = get_config_path("micro_actions_config.json")

    # Copier la config par défaut si absente
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

    # Normalise les entrées et crée un watcher pour CHACUNE (spécifique + générique)
    watchers = []
    seen = set()  # pour éviter exacts doublons (vid,pid,fw,interfaces,hash)

    for micro_name, micro_info in config.items():
        try:
            vid = int(micro_info["vendor_id"], 16)
            pid = int(micro_info["product_id"], 16)
            fw = int(micro_info["firmware"], 16)      # 0x0000 => générique (pas de filtre version)
            actions = micro_info["actions"]
            hash_value = int(micro_info.get("hash", "0x01"), 16)
            interfaces = micro_info.get("interfaces")  # None / "all" / ["col01", ...]
            settle_ms = int(micro_info.get("settle_ms", 1500))

            # -- normalisation robuste de required_prefix --
            rp = micro_info.get("required_prefix", None)

            def _normalize_prefixes(rp_val):
                # Autorise:
                #  - None
                #  - [0, 129] (liste plate -> un seul préfixe)
                #  - [[0, 129], [0, 128]] (liste de préfixes)
                #  - "[0,129]" ou "[[0,129],[0,128]]" (chaîne -> on essaie d'évaluer proprement)
                if rp_val is None:
                    return None
                if isinstance(rp_val, str):
                    s = rp_val.strip()
                    # essaye JSON-like
                    try:
                        import ast
                        val = ast.literal_eval(s)
                    except Exception:
                        # tolère "0,129" -> [0,129]
                        parts = [p.strip() for p in s.split(",") if p.strip()]
                        val = [int(p) for p in parts]
                    rp_val = val

                if isinstance(rp_val, list):
                    # liste plate -> un seul préfixe
                    if all(isinstance(x, int) for x in rp_val):
                        return [rp_val]
                    # liste de listes -> plusieurs préfixes
                    if all(isinstance(x, list) for x in rp_val):
                        return [[int(y) for y in x] for x in rp_val]
                # sinon on abandonne le filtre
                return None

            required_prefix = _normalize_prefixes(rp)
        except Exception as e:
            print(f"Erreur dans la lecture du fichier [{file}]\n{e}\n Il faut mettre à jour le fichier json !")
            return None

        key = (vid, pid, fw, str(interfaces), hash_value)
        if key in seen:
            continue
        seen.add(key)

        # Crée le watcher immédiatement : le hot-plug sera géré par monitor()/check_connection()
        watcher = BaseMic(
            loop, vid, pid, fw,
            actions, app, micro_name,
            call_back, hash=hash_value,
            interfaces=interfaces,
            settle_ms=settle_ms,
            required_prefix=required_prefix
        )
        watchers.append(watcher)

    if not watchers:
        return None
    if len(watchers) == 1:
        return watchers[0]
    # Plusieurs modèles configurés → on agrège
    return MultiMic(watchers)
