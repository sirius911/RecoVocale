import getpass


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
