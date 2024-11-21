import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://10.1.147.251:30000"  # Adresse du serveur WebSocket
    try:
        async with websockets.connect(uri) as websocket:
            print("Connexion réussie au serveur WebSocket !")

            # Exemple de message JSON à envoyer
            message = json.dumps({
                "uid": "test_client",
                "language": "en",
                "task": "transcribe"
            })
            await websocket.send(message)
            print(f"Message envoyé : {message}")

            # Lire une réponse
            response = await websocket.recv()
            print(f"Réponse reçue : {response}")
    except Exception as e:
        print(f"Erreur lors de la connexion : {e}")

asyncio.run(test_websocket())

