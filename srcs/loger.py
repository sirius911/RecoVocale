# import requests
# import socket
# import getpass
# from datetime import datetime, timezone


# def compter_mots(phrase: str) -> int:
#     # mots = re.findall(r"\b\w+(?:'\w+)?\b", phrase)
#     mots = phrase.strip().split()
#     # print(f"[LOG] Nombre de mots comptés : {len(mots)} dans la phrase : '{phrase}'")
#     return len(mots)


def envoyer_log(event="start", texte: str = "", nb_mots: int = 0,
                mode: str = "Inconnu", model: str = "Inconnu") -> None:
    """
    Envoie un événement de log au serveur distant pour journalisation.

    Cette fonction collecte des informations système (nom d'utilisateur, IP, horodatage UTC)
    et les envoie au serveur via une requête HTTP POST.

    Args:
        event (str): Type d'événement à enregistrer (ex: "start", "stop", "erreur").
        texte (str): Texte complémentaire associé à l’événement.
        mode (str): Mode d’utilisation en cours (ex: "DIRECT", "APPRENTI").
        model (str): Modèle utilisé pour la transcription.

    Returns:
        None
    """
    return  # Mode Colpo
    # if event == "transcription" and nb_mots == 0:
    #     nb_mots = compter_mots(texte)
    # try:
    #     if nb_mots > 0 or event == 'start' or event == 'stop':
    #         log_data = {
    #             "event": event,
    #             "username": getpass.getuser(),
    #             "ip": socket.gethostbyname(socket.gethostname()),
    #             "timestamp": datetime.now(timezone.utc).isoformat(),
    #             "mode": mode,
    #             "model": model,
    #             "nb_mots": nb_mots,
    #         }
    #         # print(f"[LOG] Envoi du log : {log_data}")
    #         requests.post("http://10.1.147.12:5000/log", json=log_data, timeout=2)
    # except Exception as e:
    #     print(f"[LOG] Échec d'envoi du log : {e}")
