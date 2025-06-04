import asyncio
import getpass
import json
import websockets


def get_windows_session() -> str:
    """
    Récupère le nom de session de l'utilisateur Windows actuel.

    Returns:
        str: Le nom d'utilisateur ou "None" en cas d'erreur.
    """

    try:
        return getpass.getuser()

    except Exception as e:
        print(f"[ERROR]: Impossible de récupérer la session Windows : {e}")
        return "None"


async def check_websocket_status(host: str, port: int, ip_client: str, timeout: int = 2) -> bool:
    """
    Teste la disponibilité d'un serveur WebSocket en lui envoyant un message ping
    contenant l'adresse IP du client. Attend une réponse pong.

    Args:
        host (str): Adresse IP ou nom d'hôte du serveur.
        port (int): Port utilisé par le serveur WebSocket.
        ip_client (str): Adresse IP du client (utilisée dans la requête).
        timeout (int): Délai maximal d'attente pour la connexion (en secondes).

    Returns:
        bool: True si une réponse pong est reçue, False sinon.
    """

    uri = f"ws://{host}:{port}"
    try:
        # Appliquer le timeout uniquement sur l'appel de websockets.connect
        websocket = await asyncio.wait_for(websockets.connect(uri), timeout=timeout)
        try:
            # Envoyer un message "ping" au serveur
            init_message = json.dumps({
                "uid": ip_client,
                "language": "fr",
                "task": "transcribe",
                "use_vad": True,
                "ip_client": ip_client,
                "ping": "ping",
            })
            await websocket.send(init_message)

            # Attendre la réponse du serveur
            response = await websocket.recv()
            response_data = json.loads(response)

            # Vérifier la réponse
            print(f"[INFO]: Réponse reçue : {response_data}")
            if response_data.get("ping") == "pong":
                await websocket.close(code=1000, reason=ip_client)
                return True
            else:
                print("[ERROR]: Réponse inattendue du serveur.")
                await websocket.close(code=1001, reason=ip_client)
                return False
        finally:
            await websocket.close()

    except asyncio.TimeoutError:
        print(f"[ERROR]: Connexion expirée après {timeout} secondes.")
        return False
    except Exception as e:
        print(f"[ERROR]: Erreur lors de la connexion WebSocket : {e}")
        return False


def check_server_status(host: str, port: int, ip_client: str, timeout: int = 2) -> bool:
    """
    Fonction synchrone qui encapsule `check_websocket_status` pour tester
    la connexion au serveur WebSocket, même si une boucle asyncio est déjà en cours.

    Args:
        host (str): Adresse IP ou nom d'hôte du serveur.
        port (int): Port utilisé par le serveur WebSocket.
        ip_client (str): Adresse IP du client pour identification.
        timeout (int): Délai maximal d'attente pour la réponse.

    Returns:
        bool: True si le serveur est accessible, False sinon.
    """

    try:
        # Récupérer ou créer une boucle événementielle
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Vérifier si la boucle est en cours d'exécution
        if loop.is_running():
            # Si elle tourne, exécuter dans un thread sécurisé
            future = asyncio.run_coroutine_threadsafe(
                check_websocket_status(host, port, ip_client, timeout), loop
            )
            return future.result()
        else:
            # Sinon, exécuter directement
            return loop.run_until_complete(check_websocket_status(host, port, ip_client, timeout))
    except Exception as e:
        print(f"[ERROR]: Erreur lors de la vérification du serveur : {e}")
        return False
