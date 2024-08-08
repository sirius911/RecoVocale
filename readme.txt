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
| 0.5     |            | - Icons en arrière plan pour erreur & enregistrement plus mieux !  |
|---------|------------|--------------------------------------------------------------------|

Voici le texte corrigé :

## Comment utiliser

1. Démarrez l'application.
   L'application démarre en tâche de fond.
   Un petit carré blanc apparaît. (Il se remplit de bleu s'il y a un micro et du son)
   En passant la souris sur le carré, on voit si on est connecté, la version, et la touche de raccourci.
   Avec un clic droit, on accède à un menu pour ouvrir la fenêtre principale, changer le raccourci ou quitter.

En mode Arrière-plan :
   Le mode simulation d'écriture clavier est automatiquement activé.
   Tapez la commande Raccourci pour lancer la transcription et écrire le texte transcrit.
   Le carré peut se remplir de rouge en fonction du niveau sonore.
   Retapez sur le Raccourci pour arrêter la transcription.

En mode fenêtre : 
- Cliquez sur les boutons Start et Stop pour démarrer ou arrêter la reconnaissance vocale.
- Utilisez l'option "Simule Keyboard" pour simuler la saisie dans une autre fenêtre.
  Vous pouvez alors utiliser 'Le Raccourci clavier' pour démarrer ou arrêter la reconnaissance vocale en étant dans une autre fenêtre.
- Le bouton Clear efface le contenu de la fenêtre (si la reconnaissance est en cours, le contexte est gardé et donc il peut réécrire ce qu'il a encore en mémoire.
  Pour être sûr de conserver le texte, stoppez la reconnaissance avec le bouton Stop ou le raccourci clavier).
- Le bouton Copy permet de copier le contenu de la fenêtre dans le presse-papiers.
- Le menu Paramètres permet de choisir un autre micro ou de changer de raccourci.

## Fonctionnalités

- Reconnaissance vocale en temps réel
- Simulation de la saisie au clavier
- Raccourci clavier global pour démarrer/arrêter
- Choix du micro
- Choix du raccourci Start/Stop

## Contact

Pour le support, contactez [cyrille.lorin@ch-perigueux.fr, mathias.desgranges@ch-perigueux.fr].
