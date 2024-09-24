import tkinter as tk
import win32api
import os
from utils_window import _load_and_resize_image, resource_path

def get_file_version(file_path):
    """Obtenir la version d'un fichier exécutable Windows via pywin32"""
    try:
        # Récupérer les informations de version à partir de l'exécutable
        info = win32api.GetFileVersionInfo(file_path, '\\')
        ms = info['FileVersionMS']
        ls = info['FileVersionLS']
        version = f"{ms >> 16}.{ms & 0xffff}.{ls >> 16}.{ls & 0xffff}"
        return version
    except Exception as e:
        print(f"Erreur lors de la récupération de la version : {e}")
        return "Inconnue"

def show_splash(version):
    root = tk.Tk()
    root.overrideredirect(True)  # Enlever la barre de titre
    root.geometry("400x300+500+300")  # Taille et position de la fenêtre

    try:
        logo_photo = _load_and_resize_image(resource_path("Icons/logo.png"), (150, 150))
        logo_label = tk.Label(root, image=logo_photo)
        logo_label.pack(pady=10)
    except FileNotFoundError:
        logo_label = tk.Label(root, text="Logo non trouvé", font=("Arial", 12))
        logo_label.pack(pady=10)

    # Affichage de la version du programme principal
    version_label = tk.Label(root, text=f"Version {version}", font=("Arial", 14))
    version_label.pack(pady=5)

    loading_label = tk.Label(root, text="Chargement...", font=("Arial", 12))
    loading_label.pack(pady=20)

    root.mainloop()

if __name__ == "__main__":
    # Chemin vers le fichier .exe du programme principal

    main_program_path = os.path.join(os.path.dirname(__file__), "RecoVocale.exe")

    # Vérification du chemin du fichier
    if os.path.exists(main_program_path):
        version = get_file_version(main_program_path)
    else:
        version = "Inconnue"
    # Récupérer la version du fichier exécutable
    version = get_file_version(main_program_path)

    # Afficher la fenêtre splash avec la version du programme principal
    show_splash(version)
