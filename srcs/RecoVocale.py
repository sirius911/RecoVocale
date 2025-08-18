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
from utils_socket import get_windows_session
from utils_keyboard import Simulator
from Micro import Micro
from info import VERSION, DIRECT, REDUIT, APPRENTI, FICHIER
from fenetre_debug import DebugWindow
from insertions import GestionnaireInsertion
from utils_window import get_config_path
from loger import envoyer_log
from queue_manager import UI_QUEUE
import queue
from VoiceTranscriber import VoiceTranscriber

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
        self.root.after(30, self.process_ui_queue)
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

        # Instance unique de VT
        self.vt = VoiceTranscriber(
            server_url=self.get_vt_server_url(),
            language="fr",
            device=None,
            initial_prompt='Rapport médical'
        )

        # -------------------check serveur-----------------------
        self.status_server, _ = self.vt.check_server_fast()
        self.status_server, _ = self.vt.check_server_fast()
        self._heartbeat_server_status()  # démarre le heartbeat

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

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # #---------------------------MICRO----------------------------
        # Initialize the microphone
        self.mic = Micro(loop=self.loop, app=self.current_mode, call_back=self.update)

        # Lance l'auto-découverte / auto-recréation du micro
        async def _mic_autodiscovery():
            # fréquence rapide seulement si aucun watcher n'existe
            while not getattr(self, "shutting_down", False):
                need_scan = (self.mic is None)
                if need_scan:
                    print("[AutoMic] scan…")
                    try:
                        new_mic = Micro(loop=self.loop, app=self.current_mode, call_back=self.update)
                        if new_mic:
                            self.mic = new_mic
                            # update visuelle quand on vient d’en trouver un
                            UI_QUEUE.put(self.update)
                    except Exception as e:
                        print(f"Auto-découverte micro: {e}")
                await asyncio.sleep(2 if need_scan else 10)

        # planifie la coroutine sur la boucle asyncio dédiée
        asyncio.run_coroutine_threadsafe(_mic_autodiscovery(), self.loop)

        self.info()

    def get_vt_server_url(self) -> str:
        """URL de base pour VoiceTranscriber.
        TODO : voir avec fichier configuration un truc du genre :
                f"http://{self.config.tensorRT_ip}:{self.config.port}/v1"
        """
        # base_url = "http://10.1.147.252:8000/v1"
        base_url = f"http://{self.config.server_ip}:{self.config.port}/v1"
        return base_url

    def _heartbeat_server_status(self):
        """
        Met à jour périodiquement self.status_server avec un TTL adaptatif :
        - si down -> recheck rapide (1s)
        - si up   -> recheck espacé (10s)
        """
        try:
            # ttl=None => laisse VT choisir (TTL adaptatif)
            self.status_server = self.vt.is_server_up(timeout=0.25, ttl=None)
        except Exception:
            self.status_server = False

        # prochaine exécution en fonction de l'état courant
        delay_ms = 1000 if not self.status_server else 10000
        self.update()
        self.root.after(delay_ms, self._heartbeat_server_status)

    def paste_from_clipboard(self) -> None:
        """Colle le contenu du presse-papier dans la fenêtre active via une simulation clavier."""
        self.current_mode.status_bar.config(text='- Coller -', bg='lightblue', fg='darkblue', anchor=tk.CENTER)
        Simulator([Key.ctrl, 'v'])
        time.sleep(0.5)
        self.current_mode._update_barre_status()

    def update(self) -> None:
        """Met à jour l'affichage du mode courant et les informations de débogage."""
        if hasattr(self, 'current_mode') and self.current_mode:
            self.current_mode.update()
            self.info()

    def on_closing(self) -> None:
        """Gère la fermeture de l'application en sauvegardant la configuration."""
        if getattr(self, "_closing", False):
            return
        self._closing = True
        self.shutting_down = True  # <— indique aux modes d'arrêter de poster des tâches

        # 1) arrêter proprement le mode
        try:
            if self.current_mode:
                self.current_mode.stop()
                self.current_mode.exit()
        except Exception as e:
            print("Erreur stop/exit mode:", e)

        # 2) micro
        if self.mic:
            try:
                self.mic.disconnect()
            except Exception:
                pass

        # 3) sauver la config
        self.config.shortcut = self.shortcut_manager.keyboard_shortcut
        self.config.shortcut_stop = self.shortcut_manager.stop_keyboard_shortcut
        self.config.mode = self.current_mode.name()
        self.config.x_window = self.root.winfo_x()
        self.config.y_window = self.root.winfo_y()
        self.config.save_config(self.root)

        # 4) vider la file UI pour éviter les callbacks sur des widgets détruits
        import queue as _q
        while not UI_QUEUE.empty():
            try:
                UI_QUEUE.get_nowait()
            except _q.Empty:
                break

        # 5) stop boucle + quitter Tk
        try:
            self.loop.stop()
        except Exception:
            pass
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
            if self.current_mode.mode != mode:
                log_en_cours = self.console_debug.get_log_message()
                self.current_mode.stop()
                while not UI_QUEUE.empty():
                    try:
                        UI_QUEUE.get_nowait()
                    except queue.Empty:
                        break
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

            # --- Infos VoiceTranscriber (VT) ---
            base_url = self.get_vt_server_url()
            self.console_debug.append_status_with_format("Serveur VT : ", font_style="italic")
            self.console_debug.append_status_with_format(f"{base_url}\n", color="green")

            self.console_debug.append_status_with_format("Serveur : ", font_style="italic")

            # Etat du serveur VT (check HTTP rapide)
            msg_vt = self.vt.last_health_message() or "—"
            self.console_debug.append_status_with_format("VT status : ", font_style="italic")
            self.console_debug.append_status_with_format(
                ("OK " if self.status_server else "DOWN ") + f"({msg_vt})\n",
                color=("green" if self.status_server else "red")
            )

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

    def change_shortcut(self) -> None:
        """Permet à l'utilisateur de modifier les raccourcis clavier."""
        self.shortcut_manager.change_shortcut()

    def process_ui_queue(self):
        """Traite les tâches en attente dans la file d'attente UI."""
        if getattr(self, "shutting_down", False):
            # purge silencieuse
            while not UI_QUEUE.empty():
                try:
                    UI_QUEUE.get_nowait()
                except queue.Empty:
                    break
            return  # ne replanifie pas si tu vas quitter dans la foulée

        while not UI_QUEUE.empty():
            try:
                task = UI_QUEUE.get_nowait()
                task()  # Exécute la tâche (une fonction)
            except queue.Empty:
                pass
            except Exception as e:
                print(f"Erreur dans la tâche UI : {e}")
        # Replanifie l'appel à cette méthode
        self.root.after(30, self.process_ui_queue)


def start_loop(loop: asyncio.AbstractEventLoop) -> None:
    """
    Lance la boucle asyncio dans un thread séparé.

    Args:
        loop (asyncio.AbstractEventLoop): La boucle à exécuter.
    """
    asyncio.set_event_loop(loop)
    loop.run_forever()

# def on_resize(event):
#     width = event.width
#     height = event.height
#     x = root.winfo_x()
#     y = root.winfo_y()
#     print(f"Ma fenêtre Tkinter - Dimensions: {width}x{height} - position ({x}, {y})")


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

        from threading import current_thread, main_thread
        import tkinter

        def guard(method):
            def wrapper(*a, **kw):
                if current_thread() is not main_thread():
                    msg = f"[WARN] Tk call from thread {current_thread().name}\n"
                    print(msg, end="")
                return method(*a, **kw)
            return wrapper

        tkinter.Misc.clipboard_append = guard(tkinter.Misc.clipboard_append)
        tkinter.Misc.clipboard_clear = guard(tkinter.Misc.clipboard_clear)

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
            if file_path.lower().endswith((".wav", ".mp3", ".flac", ".ogg", ".mp4")):
                print("Fichier audio détecté :", file_path)
                app.current_mode.handle_dropped_file(file_path)
                hide_drop_overlay(app)
            else:
                print("Format non supporté :", file_path)
                messagebox.showerror(
                    "Format non pris en charge",
                    f"Le fichier déposé n'est pas dans un format audio supporté.\n\nFichier :\n{file_path}")
                hide_drop_overlay(app)
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
