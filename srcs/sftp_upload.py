import paramiko

SERVER = '10.1.147.12'
PORT = 2222  # Port du serveur SFTP
USERNAME = 'ftpuser'
PASSWORD = 'DoW8EssZuCa2'  # Remplace par le mot de passe de l'utilisateur SFTP
DIRECTORY = 'data'
AUDIO_DIRECTORY = f'{DIRECTORY}/utilisateurs/audios'  # Répertoire cible dans le serveur SFTP
TEXT_DIRECTORY = f'{DIRECTORY}/utilisateurs/rapports'  # Répertoire cible dans le serveur SFTP

def ensure_directory(sftp, directory):
    """
    Vérifie si un répertoire existe et le crée s'il n'existe pas.
    """
    try:
        # Tente de lister le contenu du répertoire
        sftp.listdir(directory)
    except IOError:
        # Si une erreur survient, le répertoire n'existe pas -> on le crée
        try:
            sftp.mkdir(directory)
            print(f"Répertoire créé : {directory}")
        except Exception as e:
            print(f"Erreur lors de la création du répertoire {directory}: {e}")
            raise

def upload_files_to_sftp(audio_file, text_file, filenames):
    try:
        # Établir une connexion SFTP
        transport = paramiko.Transport((SERVER, PORT))
        transport.connect(username=USERNAME, password=PASSWORD)
        sftp = paramiko.SFTPClient.from_transport(transport)

        # Vérifie ou crée les répertoires nécessaires
        ensure_directory(sftp, DIRECTORY)  # Vérifie que 'upload' existe
        ensure_directory(sftp, AUDIO_DIRECTORY)  # Vérifie ou crée 'audios'
        ensure_directory(sftp, TEXT_DIRECTORY)  # Vérifie ou crée 'rapports'

        # Envoyer le fichier audio
        remote_audio_path = f"{AUDIO_DIRECTORY}/{filenames}.wav"
        print(f"Envoi du fichier audio : {remote_audio_path} ...", end=" ")
        sftp.put(audio_file, remote_audio_path)
        print("ok")

        # Envoyer le fichier texte
        remote_text_path = f"{TEXT_DIRECTORY}/{filenames}.txt"
        print(f"Envoi du fichier texte : {remote_text_path} ...", end=" ")
        sftp.put(text_file, remote_text_path)
        print("ok")

        # Fermer la connexion SFTP
        sftp.close()
        transport.close()
        print("Fichiers envoyés avec succès")
        return True
    except Exception as e:
        print(f"Erreur : {e}")
        return False
