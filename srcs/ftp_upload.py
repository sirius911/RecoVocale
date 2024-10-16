import ftplib
import os

SERVER = '10.1.147.12'
USERNAME = 'ftpuser'
PASSWORD = 'DoW8EssZuCa2'
AUDIO_DIRECTORY = 'audio_test'
TEXT_DIRECTORY = 'textes_test'

def upload_files_to_ftp(audio_file, text_file, filenames):
    # Connexion au serveur FTP
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
    ftp.cwd('..')

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

# Utilisation de la fonction

# audio_file = '/Users/lorcyr/data/2024100814183731.wav'
# text_file = '/Users/lorcyr/data/2024100814183731.txt'

# upload_files_to_ftp(SERVER, USERNAME, PASSWORD, audio_file, text_file)
