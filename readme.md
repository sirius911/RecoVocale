# WhisperLive Client

## Historique des versions

| Version | Date       | Modifications                                                          |
|:-------:|:----------:|:-----------------------------------------------------------------------|
|   0.1   | 2024-07-31 | Première version                                                       |
|   0.2   | 2024-07-31 | - Correction de bug de la zone de texte <br> - Bug ouput microphone                                                 |
|   0.3   | 2024-07-31 | - Ajout d'un raccourci clavier global pour démarrer/arrêter CTRL-R<br> - Correction d'un bug avec la gestion de la ponctuation                |
|   0.4   | 2024-08-02 | - Mode tache de Fond<br> - Menu Pour choisir son micro <br> - Menu pour changer son Raccourci                                      |
|   0.5   | 2024-08-12 | - Refonte threading et async function <br> - plus de menu micro <br> - Fichier user_config.ini pou Ip, Port, Shortcut, Mode <br> - Gestion Micro Philips & Nuance avec Actions paramétrable par les boutons (micro_actions_config.json)<br> - Mode Direct ou Réduit                                                |
|   0.7   | 2024-10-15 | - Mode Apprentissage <br> - Gestion des insertions automatiques                                  |
|   0.8   | 2024-11-05 | - Gestion double lancement<br> - Amélioration détection micro<br> - Amélioration system call_back                                        |
|   0.9   | 2024-11-07 | - Dictionnaire                                                         |
|   1.0   | 2024-12-01 | – Code nettoyé et mis en production                                    |
|   1.1   | 2024-12-05 | – MAJ Infos Serveur-Appli                                              |
|   1.2   | 2024-12-17 | – MAJ Infos Serveur-Appli                                              |
|   1.21  | 2024-12-18 | – MAJ pour serveur SFTP sur 10.1.147.12:2222                           |
|   1.22  | 2024-12-23 | – Ajout des interceptions des unités UI                                |
|   1.23  | 2025-04-02 | – Non significatif                                                     |
|   1.24  | 2025-04-14 | – Drag & Drop de fichiers audios<br> – Option de services (Oncologie, Cardiologie etc...)                    |
|   1.26  | 2025-05-14 | – refonte du code sur les Class Client<br> – desactivation du Drag&Drop et des Options de Services                |
|   1.30  | 2025-06-04 | – Version plus stable                                                  |
|   1.32  | 2025-07-15 | – Version avec API recovocale_engine.dll (Rust)<br> – possibilité d’utiliser les modesl sous tensorRT                      |
|   1.33  | 2025-07-18 | – utilisation de l’API pour lecture fichiers audio                     |
|   1.34  | 2025-08-06 | – utilisation de l’API pour lancer et transcrire avec VLC              |
|   1.35  | 2025-07-18 | – Patch qui fix les logs                                               |
|   2.02  | 2025-08-12 | – Version avec serveur Whisper (serveur figé sur 10.1.147.252:8000)    |
|   2.03  | 2025-08-14 | – Configuration des serveurs par fichiers de config utilisateur<br> – USB Plug & Play Opérationnel                                         |
|   2.04  | 2025-08-27 | – Dictionnaire perso avec phonème <br> – re factorisation de la fenêtre de gestion des insertions<br> – Gestion des insertions perso                                         |
|   2.05  |    ???     | – Re factorisation fenêtre Dico et gestion des dico perso <br> – Gestoin des commandes pas a pas                                      |
|   2.07  | 2025-09-04 | – CORRECTIF Pour la version v2.05 avec installation des configs de base installé dans program file/default et copie s'ils ne sont pas dans le %appData% de l’utilisateur. |
|   2.08  | 2025-09-11 | – Correctif reload insertion.xml apres modif<br> – passage du clipboard windows avec win32clipboard pour Fixer le bug dans FireFox (Xplore) |



## Comment utiliser

1. Démarrez l'application.
  

### En mode Petite Fenêtre (Mode Réduit) :
   Cliquer à l'endroit où le curseur va écrire la transcription.
   Tapez la commande Raccourci ou maintenez le bouton REC du microphone pour lancer la transcription et écrire le texte transcrit.
   Retapez sur le Raccourci pour arrêter la transcription ou lachez le bouton REC du microphone.

### En mode Grande Fenêtre (Mode Direct): 
- Cliquez sur le bouton REC / PAUSE pour démarrer ou arrêter la reconnaissance vocale.
  Vous pouvez aussi maintenir le Bouton REC du Microphone (Philips ou Nuance).
  Vous pouvez utiliser aussi le Raccourci Clavier pour lancer ou arrêter la transcription.
- Le bouton *Corbeille* efface le contenu de la Fenêtre.
  
### En mode Apprentissage (Mode apprentissage):

  Le mode apprentissage est utile pour réentraîner les modèles de reconnaissance vocale ultérieurement.

- Cliquez sur le bouton REC / PAUSE pour démarrer ou arrêter la reconnaissance vocale.
  Vous pouvez aussi maintenir le Bouton REC du Microphone (Philips ou Nuance).
  Vous pouvez utiliser aussi le Raccourci Clavier pour lancer ou arrêter la transcription.
  En mode *apprentissage*, vous ne pouvez enregistrer qu'une seule fois vos phrase.
- Le bouton *Corbeille* efface le contenu de la Fenêtre.
- Le bouton *apprentissage* envoie sur nos serveurs l'extrait audio ainsi que le texte transcrit et corrigé.
- Le bouton *casque* permet de réécouter l'extrait audio enregistré.

**IMPORTANT** : Le texte transcrit doit être à l'identique de l'extrait audio. 

## Menus
- Le menu **Paramètres** permet de:
  * Choisir ses touches de raccourci
  * Ouvrir la fenêtre de gestion des insertions 
  * Sélectionnez l'option *Debug*
  * Gérer son dictionnaire personnel
  * Gérer ses *commandes par à pas* personnelles
  * Quitter 
  
- Le menu **édition** permet de: 
  *  Copier ou coller le texte ou une sélection du texte, (avec les touches de raccourci correspondantes) 
  *  Choisir l'option *espace avant*
  *  Choisir l'option *majuscule sur la première lettre* 
 
- Le menu **Mode** permet de changer de *mode*.

## Fonctionnalit�s

- Reconnaissance vocale en temps réel
- Simulation de la saisie au clavier
- Raccourci clavier global pour démarrer/arrêter
- Bouton REC du Micro pour lancer la transcription
- Bouton EOL (Philips) ou [T->] (Nuance) pour valider un texte.
- Choix du raccourci Start/Stop
- Insertion automatique de texte préparé.
- Dictionnaire personnalisé avec phonème.
- Gestion de commande pas à pas 

## Contact

Pour le support, contactez [cyrille.lorin@ch-perigueux.fr].
