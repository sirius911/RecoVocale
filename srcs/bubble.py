import tkinter as tk
from screeninfo import get_monitors
from queue_manager import UI_QUEUE
import threading


def _show_bubble_message(parent: tk.Tk, message: str, background: str = "yellow") -> None:
    """
    Affiche ou met à jour une bulle flottante centrée sur l'écran contenant un message.

    Args:
        parent (tk.Tk): Fenêtre parente Tkinter.
        message (str): Texte à afficher.
        background (str): Couleur de fond de la bulle.
    """

    global bubble, label_in_bubble

    if bubble is not None and (
            not bubble.winfo_exists() or label_in_bubble is None or not label_in_bubble.winfo_exists()):
        bubble = None
        label_in_bubble = None
        return          # ← annule le callback résiduel

    # Obtenir les informations des écrans
    monitors = get_monitors()

    # Récupérer les coordonnées de la fenêtre principale
    parent_x = parent.winfo_rootx()
    parent_y = parent.winfo_rooty()

    # Identifier l'écran où se trouve la fenêtre principale
    for monitor in monitors:
        if (monitor.x <= parent_x < monitor.x + monitor.width and
                monitor.y <= parent_y < monitor.y + monitor.height):
            target_monitor = monitor
            break
    else:
        # Si aucun écran correspondant n'est trouvé, utiliser le premier écran
        target_monitor = monitors[0]

    screen_x = target_monitor.x
    screen_y = target_monitor.y
    screen_width = target_monitor.width
    screen_height = target_monitor.height
    if (bubble is None or not bubble.winfo_exists() or label_in_bubble is None or not label_in_bubble.winfo_exists()):
        # Widget invalide → on recrée proprement plus bas
        bubble = None
        label_in_bubble = None

    # Si la bulle existe déjà, mettre à jour le message et repositionner
    if bubble is not None:
        try:
            label_in_bubble.config(text=message)

            bubble_width = bubble.winfo_width()
            bubble_height = bubble.winfo_height()

            x = screen_x + (screen_width // 2) - (bubble_width // 2)
            y = screen_y + (screen_height // 2) - (bubble_height // 2)

            bubble.geometry(f"+{x}+{y}")
            bubble.update_idletasks()

        except tk.TclError:            # la fenêtre a été détruite juste après le test
            bubble = None
            label_in_bubble = None
            return

    else:
        # Créer la bulle
        try:
            bubble = tk.Toplevel(parent)
            bubble.wm_overrideredirect(True)
            bubble.attributes("-topmost", True)

            label_in_bubble = tk.Label(bubble, text=message, font=("Arial", 10),
                                       background=background, fg="black", borderwidth=0)
            label_in_bubble.pack(padx=10, pady=5)

            bubble_width = bubble.winfo_width()
            bubble_height = bubble.winfo_height()

            x = screen_x + (screen_width // 2) - (bubble_width // 2)
            y = screen_y + (screen_height // 2) - (bubble_height // 2)

            bubble.geometry(f"+{x}+{y}")
            bubble.update_idletasks()

        except tk.TclError as e:
            print(f"[ERROR] à la création du bubble: {e}")


def get_text_bubble() -> str:
    """
    Retourne le texte actuellement affiché dans la bulle de message.

    Returns:
        str: Texte de la bulle, ou une chaîne vide si aucune bulle n'est active.
    """

    global label_in_bubble
    try:
        if label_in_bubble is not None:
            return label_in_bubble.cget("text")
        return ""
    except tk.TclError:
        return ""


def _remove_bubble() -> str:
    """
    Ferme la bulle de message si elle existe.
    """

    global bubble, label_in_bubble
    text = ""
    try:
        if bubble is not None:
            text = get_text_bubble()
            bubble.destroy()
        # else:
        #     print("[utils_window] Aucune bulle à détruire.")
    except tk.TclError:
        # print(f"[utils_window] Erreur lors de la destruction de la bulle : {e}")
        pass
    finally:
        bubble = None
        label_in_bubble = None
        return text


def show_bubble_message(root: tk.Tk, message: str, background: str = "yellow") -> None:
    """
    Affiche ou met à jour une bulle flottante centrée sur l'écran contenant un message.

    Args:
        root (tk.Tk): Fenêtre parente Tkinter.
        message (str): Texte à afficher.
        background (str): Couleur de fond de la bulle.
    """

    def show():
        _show_bubble_message(root, message, background)

    # Ajouter la tâche à la file d'attente pour exécution dans le thread principal
    UI_QUEUE.put(show)


def remove_bubble(force: bool = False) -> str:
    """
    Ferme la bulle de message si elle existe.
    Si `force` est True, on exécute immédiatement (dans le thread courant)
    au lieu de passer par UI_QUEUE.
    """
    def remove():
        return _remove_bubble()

    if force or threading.current_thread() == threading.main_thread():
        # appel direct : on évite tout délai
        return _remove_bubble()
    else:
        UI_QUEUE.put(remove)
        return ""


def update_bubble_background(color: str) -> None:
    """
    Modifie la couleur de fond de la bulle de message active.

    Args:
        color (str): Nouvelle couleur de fond.
    """

    global label_in_bubble
    if label_in_bubble is not None:
        label_in_bubble.config(background=color)
