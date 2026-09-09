import os
import requests
import socket
import getpass
import threading
from datetime import datetime, timezone
from urllib.parse import urlparse


LOG_OK = "ok"
LOG_DISABLED = "disabled"
LOG_CONFIG_ERROR = "config_error"
LOG_SEND_ERROR = "send_error"

_STATE_LOCK = threading.Lock()
_serv_log = ""
_log_status = LOG_CONFIG_ERROR
_log_error = ""
_log_config_path = ""


def _set_log_state(status: str, error: str = "") -> None:
    global _log_status, _log_error
    with _STATE_LOCK:
        _log_status = status
        _log_error = error


def _set_log_config(serv_log: str, config_path: str) -> None:
    global _serv_log, _log_config_path
    with _STATE_LOCK:
        _serv_log = serv_log
        _log_config_path = config_path


def get_log_status() -> str:
    with _STATE_LOCK:
        return _log_status


def get_log_info() -> dict:
    """Retourne un instantané de l'état du système de logs."""
    with _STATE_LOCK:
        return {
            "status": _log_status,
            "server": _serv_log,
            "error": _log_error,
            "config_path": _log_config_path,
        }


def initialiser_log() -> None:
    """
    Charge la politique machine de journalisation.

    Source d'autorité :
        %PROGRAMDATA%\\RecoVocale\\serv_log.inf

    Valeurs acceptées :
        - une URL HTTP/HTTPS : logs actifs
        - no_log             : logs désactivés

    En cas de fichier absent, vide, illisible ou invalide, aucun log n'est envoyé
    et l'état passe à LOG_CONFIG_ERROR.
    """
    program_data = os.getenv("PROGRAMDATA")
    if not program_data:
        _set_log_config("", "")
        _set_log_state(
            LOG_CONFIG_ERROR,
            "Variable d'environnement PROGRAMDATA introuvable."
        )
        print("[LOG] Configuration invalide : PROGRAMDATA introuvable.")
        return

    config_path = os.path.join(program_data, "RecoVocale", "serv_log.inf")
    _set_log_config("", config_path)

    try:
        with open(config_path, "r", encoding="utf-8-sig") as fichier:
            contenu = fichier.read().strip()
    except Exception as e:
        _set_log_state(
            LOG_CONFIG_ERROR,
            f"Impossible de lire {config_path} : {e}"
        )
        print(f"[LOG] Configuration invalide : impossible de lire {config_path} : {e}")
        return

    if not contenu:
        _set_log_state(
            LOG_CONFIG_ERROR,
            f"Le fichier {config_path} est vide."
        )
        print(f"[LOG] Configuration invalide : {config_path} est vide.")
        return

    if "\n" in contenu or "\r" in contenu:
        _set_log_state(
            LOG_CONFIG_ERROR,
            f"Le fichier {config_path} doit contenir une seule ligne."
        )
        print(f"[LOG] Configuration invalide : {config_path} doit contenir une seule ligne.")
        return

    if contenu.casefold() == "no_log":
        _set_log_config("", config_path)
        _set_log_state(LOG_DISABLED)
        print(f"[LOG] Envoi des logs désactivé par {config_path}.")
        return

    parsed = urlparse(contenu)
    if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
        _set_log_state(
            LOG_CONFIG_ERROR,
            f"Valeur invalide dans {config_path} : {contenu!r}"
        )
        print(f"[LOG] Configuration invalide dans {config_path} : {contenu!r}")
        return

    _set_log_config(contenu, config_path)
    _set_log_state(LOG_OK)
    print(f"[LOG] Serveur configuré : {contenu}")


def compter_mots(phrase: str) -> int:
    mots = phrase.strip().split()
    return len(mots)


def envoyer_log(event="start", texte: str = "", nb_mots: int = 0,
                mode: str = "Inconnu", model: str = "Inconnu") -> None:
    """
    Envoie un événement de log au serveur configuré par serv_log.inf.

    Aucun envoi n'est tenté si les logs sont désactivés ou si la configuration
    machine est invalide.
    """
    if event == "transcription" and nb_mots == 0:
        nb_mots = compter_mots(texte)

    info = get_log_info()
    serv_log = info["server"]

    # no_log ou erreur de configuration : aucun trafic réseau.
    if not serv_log:
        return

    if not (nb_mots > 0 or event == "start" or event == "stop"):
        return

    try:
        log_data = {
            "event": event,
            "username": getpass.getuser(),
            "ip": socket.gethostbyname(socket.gethostname()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": mode,
            "model": model,
            "nb_mots": nb_mots,
        }

        response = requests.post(serv_log, json=log_data, timeout=2)
        response.raise_for_status()

        # Un nouvel envoi réussi efface une éventuelle erreur précédente.
        _set_log_state(LOG_OK)

    except Exception as e:
        _set_log_state(LOG_SEND_ERROR, str(e))
        print(f"[LOG] Échec d'envoi du log vers {serv_log} : {e}")
