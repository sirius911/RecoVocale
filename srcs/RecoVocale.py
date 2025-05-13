import os
import socket
import time
import tkinter as tk
from tkinterdnd2 import TkinterDnD
import asyncio
import threading
import keyboard
from shortcut_manager import ShortcutManager
from UserConfig import UserConfig
from Mode_Direct import Mode_Direct
from Mode_Apprenti import Mode_Apprenti
from Mode_Reduit import Mode_Reduit
from utils_socket import check_server_status, get_windows_session
from utils_keyboard import Simulator
from Micro import Micro
from info import *
from pynput.keyboard import Key
from fenetre_debug import DebugWindow
from insertions import GestionnaireInsertion
from utils_window import get_config_path
import win32api
import sys
import win32event
import winerror
from tkinter import messagebox
import atexit
from loger import envoyer_log

atexit.register(lambda: envoyer_log("stop"))

class App:
    def __init__(self, root, loop):
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
 
        #-------------------check serveur-----------------------
        self.status_server = check_server_status(self.config.server_ip, self.config.port, self.ip_client, timeout=5)

        #----------------------MODE----------------------------
        mode = self.config.mode
        if mode == "APPRENTI":
            self.current_mode = Mode_Apprenti(self)
        elif mode == "REDUIT":
            self.current_mode = Mode_Reduit(self)
        else: # Default to DIRECT mode
            self.current_mode = Mode_Direct(self)

        self.shortcut_manager = ShortcutManager(root, self.current_mode, self.config.shortcut)
        try: #Verifier le raccourcis qui peut planter
            keyboard.add_hotkey(self.shortcut_manager.keyboard_shortcut, self.current_mode.toggle_start_stop)
        except Exception:
            keyboard.add_hotkey("F3", self.current_mode.toggle_start_stop)

        self.root.protocol("WM_DELETE_WINDOW", self.current_mode.exit_app)

        # #---------------------------MICRO----------------------------
        # Initialize the microphone 
        self.mic = Micro(loop=self.loop, app=self.current_mode, call_back=self.update)
        self.info()

    def paste_from_clipboard(self):
        self.current_mode.status_bar.config(text='- Coller -', bg='lightblue', fg='darkblue', anchor=tk.CENTER)
        Simulator([Key.ctrl, 'v'])
        time.sleep(0.5)
        self.current_mode._update_barre_status()
            
    def running(self):
        return self.client_manager.running

    def update(self):
        if self.current_mode:
            self.current_mode.update() 
            self.info()

    def on_closing(self):
        self.current_mode.stop()
        if self.mic:
            self.mic.disconnect()
        # sauvegarde userConfig
        self.config.shortcut = self.shortcut_manager.keyboard_shortcut
        self.config.mode = self.current_mode.name()
        self.config.x_window = self.root.winfo_rootx()
        self.config.y_window = self.root.winfo_rooty()
        self.config.save_config(self.root)
        self.loop.stop()
        self.root.quit()

    def switch_mode(self, mode):
        if self.config.debug:
            print(f"switch_mode({mode.name})")
        if self.current_mode:
            if self.current_mode.mode != mode:
                self.current_mode.stop()
                log_en_cours = self.console_debug.get_log_message()
                text_en_cours = self.current_mode.exit()
                self.current_mode = None
                if mode == DIRECT:
                    self.current_mode = Mode_Direct(self)
                    self.current_mode.update_transcriptions(message=text_en_cours, ending=True)
                elif mode == APPRENTI:
                    self.current_mode = Mode_Apprenti(self)
                elif mode == REDUIT:
                    self.current_mode = Mode_Reduit(self)
                    self.current_mode.update_transcriptions(message=text_en_cours, ending=True)
                else:
                    self.console_debug.log_message("Erreur de Mode dans App")
                    self.on_closing()

                # Utiliser after_idle pour s'assurer que geometry est bien appliqué
                self.root.after_idle(lambda: self.root.geometry(f"{self.current_mode.mode.window_width}x{self.current_mode.mode.window_height}+{self.config.x_window}+{self.config.y_window}"))
                if self.mic:
                    self.mic.change_mode(self.current_mode)
                keyboard.clear_all_hotkeys()
                keyboard.add_hotkey(self.shortcut_manager.keyboard_shortcut, self.current_mode.toggle_start_stop)

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
    
    def info(self):
        if self.config.debug:
            self.console_debug.delete_status()
            self.console_debug.append_status_with_format("Version : ", font_style="italic")
            self.console_debug.append_status_with_format(f"v{VERSION}\n", color="green")
            self.console_debug.append_status_with_format("Modèle : ", font_style="italic")
            if self.current_mode.client_manager.client:
                self.console_debug.append_status_with_format(f"{self.current_mode.client_manager.client.get_model_path()}\n", color="green")
            else:
                self.console_debug.append_status_with_format("None\n", color="blue")
            self.console_debug.append_status_with_format("Serveur : ", font_style="italic")
            if check_server_status(self.config.server_ip, self.config.port, self.ip_client):
                self.console_debug.append_status_with_format(f"Connected @{self.config.server_ip}:{self.config._port} \n", color="green")
            else:
                self.console_debug.append_status_with_format(f"NOT Connected @{self.config.server_ip}:{self.config.port} \n", color="red")
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
            self.console_debug.append_status_with_format(" - Simul Clavier : ", font_style="italic")
            self.console_debug.append_status_with_format(f" {'Oui' if self.current_mode.simulator_keyboard else 'Non'}\n", color="green")
            
            self.console_debug.append_status_with_format("Raccourci : ", font_style="italic")
            self.console_debug.append_status_with_format(f"{self.shortcut_manager.keyboard_shortcut}\n", color="green")

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

    def change_shortcut(self):
        self.shortcut_manager.change_shortcut()


def start_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

def on_resize(event):
        width = event.width
        height = event.height
        print(f"Ma fenêtre Tkinter - Dimensions: {width}x{height}")

def show_drop_overlay(app):
    app.drop_label = tk.Label(app.root, text="📁 Déposez ici", font=("Arial", 24), bg="yellow", fg="black")
    app.drop_label.place(relx=0.5, rely=0.5, anchor="center")

def hide_drop_overlay(app):
    if hasattr(app, 'drop_label'):
        app.drop_label.destroy()
        del app.drop_label



if __name__ == "__main__":
    #mutex unique pour l'application
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
                messagebox.showerror("Format non pris en charge",
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