# import socket


# def check_server_status(host:str, port:int) -> bool:
#         try:
#             sock = socket.create_connection((host, port), timeout=2)
#             sock.close()
#             return True
#         except (socket.timeout, ConnectionRefusedError, socket.gaierror, OSError):
#             return False

import asyncio
import websockets

async def check_websocket_status(host: str, port: int) -> bool:
    uri = f"ws://{host}:{port}"
    try:
        async with websockets.connect(uri) as websocket:
            return True
    except Exception as e:
        return False


def check_server_status(host: str, port: int) -> bool:
    try:
        # Vérifier si une boucle événementielle existe
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # Créer une nouvelle boucle si aucune n'existe
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Si la boucle est en cours d'exécution, exécuter dans un thread sécurisé
        if loop.is_running():
            future = asyncio.run_coroutine_threadsafe(
                check_websocket_status(host, port), loop
            )
            return future.result()
        else:
            # Sinon, exécuter directement avec run
            return loop.run_until_complete(check_websocket_status(host, port))
    except Exception as e:
        print(f"Erreur lors de la vérification du serveur : {e}")
        return False
