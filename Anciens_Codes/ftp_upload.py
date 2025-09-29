import ftplib

SERVER = '10.1.147.12'
USERNAME = 'ftpuser'
PASSWORD = 'password'
AUDIO_DIRECTORY = '/var/ftp/utilisateurs/audios'
TEXT_DIRECTORY = '/var/ftp/utilisateurs/rapports'


def upload_files_to_ftp(audio_file: str, text_file: str, filenames: str) -> bool:
    """
    Envoie un fichier audio et un fichier texte sur un serveur FTP distant.

    Le fichier audio est stocké dans le dossier AUDIO_DIRECTORY et le fichier texte dans TEXT_DIRECTORY,
    tous deux nommés selon la chaîne `filenames` (avec extensions `.wav` et `.txt` respectivement).

    Args:
        audio_file (str): Chemin local vers le fichier audio à envoyer.
        text_file (str): Chemin local vers le fichier texte à envoyer.
        filenames (str): Nom de base des fichiers (sans extension) à utiliser sur le serveur.

    Returns:
        bool: True si l'opération a réussi, False sinon.
    """

    try:
        ftp = ftplib.FTP(SERVER)
        ftp.login(user=USERNAME, passwd=PASSWORD)
    except Exception as e:
        print(f"Erreur: {e}")
        return False

    # Création du répertoire 'audio/' s'il n'existe pas et changement de répertoire
    try:
        ftp.mkd(AUDIO_DIRECTORY)
    except ftplib.error_perm as e:
        if not str(e).startswith('550'):  # Le code d'erreur 550 signifie que le répertoire existe déjà
            raise
    except Exception as e:
        print(f"Erreur: {e}")
        return False
    ftp.cwd(AUDIO_DIRECTORY)

    # Envoi du fichier audio
    with open(audio_file, 'rb') as file:
        ftp.storbinary(f'STOR {filenames}.wav', file)

    # Revenir à la racine du serveur
    # ftp.cwd('..')

    # Création du répertoire 'textes/' s'il n'existe pas et changement de répertoire
    try:
        ftp.mkd(TEXT_DIRECTORY)
    except ftplib.error_perm as e:
        if not str(e).startswith('550'):  # 550 signifie que le répertoire existe déjà
            raise
    except Exception as e:
        print(f"Erreur: {e}")
        return False

    ftp.cwd(TEXT_DIRECTORY)

    # Envoi du fichier texte
    with open(text_file, 'rb') as file:
        ftp.storbinary(f'STOR {filenames}.txt', file)

    # Fermeture de la connexion FTP
    ftp.quit()
    print("Fichiers envoyés avec succès")
    return True
