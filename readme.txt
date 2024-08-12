# WhisperLive Client

## Historique des versions

|---------|------------|--------------------------------------------------------------------|
| Version | Date       | Modifications                                                      |
|---------|------------|--------------------------------------------------------------------|
| 0.1     | 2024-07-31 | Première version                                                   |
| 0.2     | 2024-07-31 | - Correction de bug de la zone de texte                            |
|         |            | - Bug ouput microphone                                             |
| 0.3     | 2024-07-31 | - Ajout d'un raccourci clavier global pour démarrer/arrêter CTRL-R |
|         |            | - Correction d'un bug avec la gestion de la ponctuation            |
| 0.4     | 2024-08-02 | - Mode tache de Fond                                               |
|         |            | - Menu Pour choisir son micro                                      |
|         |            | - Menu pour changer son Raccourci                                  |
| 0.5     | 2024-08-12 | - Refonte threading et async function                              |
|         |            | - plus de menu micro                                               |
|         |            | - Fichier user_config.ini pou Ip, Port, Shortcut, Mode             |
|         |            | - Gestion Micro Philips & Nuance avec Actions paramètrable par les |
|         |            |   boutons (micro_actions_config.json)                              |
|         |            | - Mode GrandeFenêtre ou petite Fenêtre                             |
|---------|------------|--------------------------------------------------------------------|

## Comment utiliser

1. Dï¿½marrez l'application.
  

En mode Petite fenètre :
   Le mode simulation d'écriture clavier est automatiquement activé.
   Tapez la commande Raccourci ou maintenez le bouton REC du microphone pour lancer la transcription et écrire le texte transcrit.
   Retapez sur le Raccourci pour arrêter la transcription ou lachez le bouton REC du microphone

En mode Grande fenêtre : 
- Cliquez sur le bouton REC / PAUSE pour démarrer ou arrêter la reconnaissance vocale.
  Vous pouvez aussi maintenir le Bouton REC du Microphone (Philips ou Nuance).
  Vous pouvez utiliser aussi le Raccourci Clavier pour lancer ou arrêter la transcription.
- Utilisez l'option "Simule Keyboard" pour simuler la saisie dans une autre fenêtre.
- Le bouton Clear efface le contenu de la fenêtre.
- Le bouton Copy permet de copier le contenu de la fenêtre dans le presse-papiers.
- Le bouton Validation 'fige' le texte. Cela ferme et reouvre une session websocket. 
- Le menu Paramètres permet de changer de raccourci.

## Fonctionnalités

- Reconnaissance vocale en temps réel
- Simulation de la saisie au clavier
- Raccourci clavier global pour démarrer/arrêter
- Bouton REC du Micro pour lancer la transcription
- Bouton EOL (Philips) ou [T->] (Nuance) pour valider un texte.
- Choix du raccourci Start/Stop 

## Contact

Pour le support, contactez [cyrille.lorin@ch-perigueux.fr, mathias.desgranges@ch-perigueux.fr].
