import requests
import socket
import getpass
from datetime import datetime, timezone

def envoyer_log(event="start", texte ="", mode="Inconnu", model="Inconnu"):
    try:
        log_data = {
            "event": event,
            "username": getpass.getuser(),
            "ip": socket.gethostbyname(socket.gethostname()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": mode,
            "model": model,
            "texte": texte,
        }
        requests.post("http://10.1.147.12:5000/log", json=log_data, timeout=2)
    except Exception as e:
        print(f"[LOG] Échec d'envoi du log : {e}")
