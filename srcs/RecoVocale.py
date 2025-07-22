import os
import socket
import time
import tkinter as tk
import asyncio
import threading
import keyboard
import atexit
import sys
import win32api
import win32event
import winerror
from tkinter import messagebox
from tkinterdnd2 import TkinterDnD
from pynput.keyboard import Key
from shortcut_manager import ShortcutManager
from UserConfig import UserConfig
from Mode_Direct import Mode_Direct
from Mode_Apprenti import Mode_Apprenti
from Mode_Reduit import Mode_Reduit
from Mode_Fichier import Mode_Fichier
from utils_socket import check_server_status, get_windows_session
from utils_keyboard import Simulator
from Micro import Micro
from info import VERSION, DIRECT, REDUIT, APPRENTI, FICHIER
from fenetre_debug import DebugWindow
from insertions import GestionnaireInsertion
from utils_window import get_config_path
from loger import envoyer_log

# Envoi d'un log "stop" à la fermeture du programme
atexit.register(lambda: envoyer_log("stop"))


class App:
    """Classe principale de l'application RecoVocale.

    Gère l'initialisation, le changement de mode, les raccourcis, le microphone et la fenêtre principale.
    """
    def __init__(self, root: tk.Tk, loop: asyncio.AbstractEventLoop) -> None:
        """
        Initialise l'application avec la fenêtre principale et la boucle asyncio.

        Args:
            root (tk.Tk): La fenêtre principale Tkinter.
            loop (asyncio.AbstractEventLoop): La boucle asyncio utilisée par l'application.
        """
        self.config = UserConfig()
        self.insertions = GestionnaireInsertion(self.config.insertions)
        self.console_debug = DebugWindow(root)
        self.debug_window_id = self.console_debug.debug_window.winfo_id()

        if self.config.debug:
            self.console_debug.debug_window.deiconify()  # Afficher la fenêtre de débogage
        else:
            self.console_debug.debug_window.withdraw()

        self.root = root
        # Récupérer l'adresse IP locale du client
        try:
            self.ip_client = socket.gethostbyname(socket.gethostname())
        except Exception:
            self.ip_client = "0.0.0.0"  # Fallback si l'IP n'est pas détectée
        self.ip_client = f"{get_windows_session()}@{self.ip_client}"
        # Use the provided asyncio event loop
        self.loop = loop
        self.recording = False
        self.root.attributes("-topmost", True)  # Keep the window on top of others

        # -------------------check serveur-----------------------
        self.status_server = check_server_status(self.config.server_ip, self.config.port, self.ip_client, timeout=5)

        # ----------------------MODE----------------------------
        mode = self.config.mode
        if mode == "APPRENTI":
            self.current_mode = Mode_Apprenti(self)
        elif mode == "REDUIT":
            self.current_mode = Mode_Reduit(self)
        else:  # Default to DIRECT mode
            self.current_mode = Mode_Direct(self)

        # ---- Touches de racourcis
        self.shortcut_manager = ShortcutManager(
            root,
            self.current_mode,
            self.config.shortcut,
            self.config.shortcut_stop
        )

        # Enregistrer les deux raccourcis s’ils sont valides
        try:
            if self.shortcut_manager.keyboard_shortcut:
                keyboard.add_hotkey(self.shortcut_manager.keyboard_shortcut, self.current_mode.toggle_start_stop)
            if self.shortcut_manager.stop_keyboard_shortcut:
                keyboard.add_hotkey(self.shortcut_manager.stop_keyboard_shortcut, self.current_mode.stop)
        except Exception:
            keyboard.add_hotkey("F3", self.current_mode.toggle_start_stop)
            keyboard.add_hotkey("F4", self.current_mode.stop)

        self.root.protocol("WM_DELETE_WINDOW", self.current_mode.exit_app)

        # #---------------------------MICRO----------------------------
        # Initialize the microphone
        self.mic = Micro(loop=self.loop, app=self.current_mode, call_back=self.update)
        self.info()

    def paste_from_clipboard(self) -> None:
        """Colle le contenu du presse-papier dans la fenêtre active via une simulation clavier."""
        self.current_mode.status_bar.config(text='- Coller -', bg='lightblue', fg='darkblue', anchor=tk.CENTER)
        Simulator([Key.ctrl, 'v'])
        time.sleep(0.5)
        self.current_mode._update_barre_status()

    def running(self) -> bool:
        """
        Renvoie l'état d'exécution du client manager.

        Returns:
            bool: True si le client est actif, False sinon.
        """
        if self.current_mode.client_manager:
            return self.client_manager.running

    def update(self) -> None:
        """Met à jour l'affichage du mode courant et les informations de débogage."""
        if self.current_mode:
            self.current_mode.update()
            self.info()

    def on_closing(self) -> None:
        """Gère la fermeture de l'application en sauvegardant la configuration."""
        self.current_mode.stop()
        self.current_mode.exit()
        if self.mic:
            self.mic.disconnect()
        # sauvegarde userConfig
        self.config.shortcut = self.shortcut_manager.keyboard_shortcut
        self.config.shortcut_stop = self.shortcut_manager.stop_keyboard_shortcut
        self.config.mode = self.current_mode.name()
        self.config.x_window = self.root.winfo_rootx()
        self.config.y_window = self.root.winfo_rooty()
        self.config.save_config(self.root)
        self.loop.stop()
        self.root.quit()

    def switch_mode(self, mode) -> None:
        """
        Permet de changer dynamiquement de mode d'utilisation.

        Args:
            mode: Le nouveau mode à activer.
        """
        if self.config.debug:
            print(f"switch_mode({mode.name})")
        if self.current_mode:
            # last_model = self.current_mode.engine.model
            if self.current_mode.mode != mode:
                log_en_cours = self.console_debug.get_log_message()
                self.current_mode.stop()
                self.current_mode.exit()
                # log_en_cours = self.console_debug.get_log_message()
                self.current_mode = None
                if mode == DIRECT:
                    self.current_mode = Mode_Direct(self)
                    time.sleep(0.5)
                elif mode == APPRENTI:
                    self.current_mode = Mode_Apprenti(self)
                elif mode == REDUIT:
                    self.current_mode = Mode_Reduit(self)
                elif mode == FICHIER:
                    self.current_mode = Mode_Fichier(self)
                else:
                    self.console_debug.log_message("Erreur de Mode dans App")
                    self.on_closing()

                if self.mic:
                    self.mic.change_mode(self.current_mode)

                # touches de Raccourcis
                keyboard.clear_all_hotkeys()
                if self.shortcut_manager.keyboard_shortcut:
                    keyboard.add_hotkey(self.shortcut_manager.keyboard_shortcut, self.current_mode.toggle_start_stop)
                if self.shortcut_manager.stop_keyboard_shortcut:
                    keyboard.add_hotkey(self.shortcut_manager.stop_keyboard_shortcut, self.current_mode.stop)

                try:
                    if self.config.debug:
                        self.console_debug.debug_window.deiconify()
                    else:
                        self.console_debug.debug_window.withdraw()
                except tk.TclError:
                    # La fenêtre a été détruite, on la recrée proprement
                    self.console_debug = DebugWindow(self.root)
                    if self.config.debug:
                        self.console_debug.debug_window.deiconify()
                    else:
                        self.console_debug.debug_window.withdraw()

                self.info()
                self.console_debug.log_message(log_en_cours)

    def info(self) -> None:
        """Affiche les informations de débogage si activé."""
        if self.config.debug:
            self.console_debug.delete_status()
            self.console_debug.append_status_with_format("Version : ", font_style="italic")
            self.console_debug.append_status_with_format(f"v{VERSION}\n", color="green")
            self.console_debug.append_status_with_format("Version DLL : ", font_style="italic")
            self.console_debug.append_status_with_format(f"{self.current_mode.engine.version_dll}\n", color="green")
            self.console_debug.append_status_with_format("backend : ", font_style="italic")
            self.console_debug.append_status_with_format(f"{self.current_mode.engine.backend}\n", color="green")
            self.console_debug.append_status_with_format("Modèle : ", font_style="italic")
            self.console_debug.append_status_with_format(f"{self.current_mode.engine.model}\n", color="green")

            self.console_debug.append_status_with_format("Serveur : ", font_style="italic")
            if check_server_status(self.config.server_ip, self.config.port, self.ip_client):
                self.console_debug.append_status_with_format(
                    f"Connected @{self.config.server_ip}:{self.config._port}\n", color="green")
            else:
                self.console_debug.append_status_with_format(
                    f"NOT Connected @{self.config.server_ip}:{self.config.port}\n", color="red")

            self.console_debug.append_status_with_format("Service : ", font_style="italic")
            self.console_debug.append_status_with_format(f"{self.config.service}\n", color="green")
            self.console_debug.append_status_with_format("IP client : ", font_style="italic")
            self.console_debug.append_status_with_format(f"{self.ip_client}\n", color="green")
            self.console_debug.append_status_with_format("Micro : ", font_style="italic")
            if self.mic and self.mic.is_connected():
                self.console_debug.append_status_with_format(f"{self.mic.micro_name}\n", color="green")
            else:
                self.console_debug.append_status_with_format("Aucun\n", color="red")

            self.console_debug.append_status_with_format("Mode : ", font_style="italic")
            self.console_debug.append_status_with_format(self.current_mode.name(), color="green")

            self.console_debug.append_status_with_format("Raccourci rec/pause : ", font_style="italic")
            self.console_debug.append_status_with_format(f"{self.shortcut_manager.keyboard_shortcut}\n", color="green")

            self.console_debug.append_status_with_format("Raccourci arrêt transcription : ", font_style="italic")
            self.console_debug.append_status_with_format(f"{self.shortcut_manager.stop_keyboard_shortcut or '—'}\n",
                                                         color="green")

            self.console_debug.append_status_with_format("Debug : ", font_style="italic")
            self.console_debug.append_status_with_format(f"{self.config.debug}\n", color="green")

            self.console_debug.append_status_with_format("Position actuelle de la fenêtre : x=", font_style="italic")
            self.console_debug.append_status_with_format(self.root.winfo_x(), color="green")
            self.console_debug.append_status_with_format(", y=", font_style="italic")
            self.console_debug.append_status_with_format(f"{self.root.winfo_y()}\n", color="green")

            self.console_debug.append_status_with_format("Fichier des insertions : ", font_style="italic")
            self.console_debug.append_status_with_format(f"{get_config_path(self.config.insertions)}\n", color="green")

            self.console_debug.append_status_with_format("Nb répétitions : ", font_style="italic")
            self.console_debug.append_status_with_format(f"{self.config.nb_repeat}", color="green")

    def change_shortcut(self) -> None:
        """Permet à l'utilisateur de modifier les raccourcis clavier."""
        self.shortcut_manager.change_shortcut()


def start_loop(loop: asyncio.AbstractEventLoop) -> None:
    """
    Lance la boucle asyncio dans un thread séparé.

    Args:
        loop (asyncio.AbstractEventLoop): La boucle à exécuter.
    """
    asyncio.set_event_loop(loop)
    loop.run_forever()

# def on_resize(event):
#         width = event.width
#         height = event.height
#         print(f"Ma fenêtre Tkinter - Dimensions: {width}x{height}")


def show_drop_overlay(app: App) -> None:
    """Affiche un label de dépôt sur la fenêtre principale."""
    app.drop_label = tk.Label(app.root, text="📁 Déposez ici", font=("Arial", 24), bg="yellow", fg="black")
    app.drop_label.place(relx=0.5, rely=0.5, anchor="center")


def hide_drop_overlay(app: App) -> None:
    """Supprime le label de dépôt de la fenêtre principale."""
    if hasattr(app, 'drop_label'):
        app.drop_label.destroy()
        del app.drop_label


if __name__ == "__main__":
    """
    Point d'entrée principal du programme.
    Vérifie qu'une seule instance est en cours grâce à un mutex Windows,
    puis initialise la fenêtre Tkinter, l'application et les événements DnD.
    """
    # mutex unique pour l'application
    mutex_name = "recovocale_mutex"
    mutex = win32event.CreateMutex(None, False, mutex_name)

    # Si le mutex existe déjà, cela signifie que l'application est déjà en cours d'exécution
    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
        print("Le programme est déjà en cours d'exécution.")
        sys.exit(0)
    else:
        envoyer_log("start")
    try:

        root = TkinterDnD.Tk()
        # Chemin vers l'icône (dans le répertoire de l'application installée)
        if getattr(sys, 'frozen', False):  # Mode exécutable compilé
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(base_path, "Icons/reco.ico")
        # Définir l'icône de la fenêtre principale
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
        else:
            print("Icône non trouvée :", icon_path)
        # Create a new event loop
        new_loop = asyncio.new_event_loop()
        threading.Thread(target=start_loop, args=(new_loop,), daemon=True).start()

        app = App(root, new_loop)  # Pass the new loop to the app
        # root.bind("<Configure>", on_resize)

        def on_file_drop(event):
            file_path = event.data.strip("{}")  # Nettoyer le nom du fichier
            if file_path.lower().endswith((".wav", ".mp3", ".flac", ".ogg")):
                print("Fichier audio détecté :", file_path)
                app.current_mode.handle_dropped_file(file_path)
                hide_drop_overlay(app)
            else:
                print("Format non supporté :", file_path)
                messagebox.showerror(
                    "Format non pris en charge",
                    f"Le fichier déposé n'est pas dans un format audio supporté.\n\nFichier :\n{file_path}")
                return

        # Activer le drop sur la fenêtre principale
        root.drop_target_register('DND_Files')
        root.dnd_bind('<<Drop>>', on_file_drop)
        root.dnd_bind('<<DropEnter>>', lambda e: show_drop_overlay(app))
        root.dnd_bind('<<DropLeave>>', lambda e: hide_drop_overlay(app))

        root.mainloop()
        # Une fois terminé, relâchez le mutex
        if mutex:
            win32api.CloseHandle(mutex)

        print("Bye!")
    except Exception as e:
        print(e)
