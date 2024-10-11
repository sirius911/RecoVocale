import time
import tkinter as tk
from tkinter import messagebox
import asyncio
import threading
import keyboard

from UserConfig import UserConfig
from Mode_Direct import Mode_Direct
from Mode_Apprenti import Mode_Apprenti
from Mode_Record import Mode_Record
from Mode_Reduit import Mode_Reduit
from utils_socket import check_server_status
from utils_keyboard import Simulator
from Micro import Micro
from info import *
from pynput.keyboard import Key
from fenetre_debug import DebugWindow
from insertions import GestionnaireInsertion
from utils_window import get_config_path


class App:
    def __init__(self, root, loop):
        self.config = UserConfig()
        self.insertions = GestionnaireInsertion(self.config.insertions)
        self.console_debug = DebugWindow(root)
        if self.config.debug:
           self.console_debug.debug_window.deiconify()  # Afficher la fenêtre de débogage
        else:
            self.console_debug.debug_window.withdraw()
       
        self.root = root
        
        # Use the provided asyncio event loop
        self.loop = loop
        self.recording = False
        self.root.attributes("-topmost", True)  # Keep the window on top of others
 
        #-------------------check serveur-----------------------
        self.status_server = check_server_status(self.config.server_ip, self.config.port)

        #-----------------Shortcut------------------------------
        self.keyboard_shortcut = self.config.shortcut
        #----------------------MODE----------------------------
        mode = self.config.mode
        if mode == "RECORD":
            self.current_mode = Mode_Record(self)
        elif mode == "APPRENTI":
            self.current_mode = Mode_Apprenti(self)
        elif mode == "REDUIT":
            self.current_mode = Mode_Reduit(self)
        else:
            self.current_mode = Mode_Direct(self)
       
        try: #Verifier le raccourcis qui peut planter
            keyboard.add_hotkey(self.keyboard_shortcut, self.current_mode.toggle_start_stop)
        except Exception:
            keyboard.add_hotkey("F3", self.current_mode.toggle_start_stop)

        self.root.protocol("WM_DELETE_WINDOW", self.current_mode.exit_app)

        # #---------------------------MICRO----------------------------
        # Initialize the microphone 
        # self.mic = Micro(loop, app=self.current_mode)
        self.mic = None
        self.root.after(100, self.start_micro_monitoring)  # Démarrer l'intégration asyncio/tkinter
        self.info()

    def start_micro_monitoring(self):
        """Démarre la surveillance du micro via la méthode monitor() de Micro."""
        if self.mic is None:
            try:
                self.mic = Micro(loop=self.loop, app=self.current_mode, call_back=self.info)
                self.current_mode.status_bar.config(text=f'[{self.mic.micro_name}] connecté', bg='lightblue', fg='darkblue', anchor=tk.CENTER)
            except Exception as e:
                self.current_mode.status_bar.config(text='Micro déconnecté', bg='lightblue', fg='darkblue', anchor=tk.CENTER)
        if self.mic:
            asyncio.run_coroutine_threadsafe(self.mic.monitor(), self.loop)

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
        # self.stop_client()
        if self.mic:
            self.mic.disconnect()
        # sauvegarde userConfig
        self.config.shortcut = self.keyboard_shortcut
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
                elif mode == RECORD:
                    self.current_mode = Mode_Record(self)
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
                keyboard.add_hotkey(self.keyboard_shortcut, self.current_mode.toggle_start_stop)

                # recréation de la fenetre debug
                self.console_debug = DebugWindow(root)
                if self.config.debug:
                    self.console_debug.debug_window.deiconify()  # Afficher la fenêtre de débogage
                else:
                    self.console_debug.debug_window.withdraw()
                self.info()
                self.console_debug.log_message(log_en_cours)
    
    def info(self):
        self.console_debug.delete_status()
        self.console_debug.append_status_with_format("Version : ", font_style="italic")
        self.console_debug.append_status_with_format(f"v{VERSION}\n", color="green")
        self.console_debug.append_status_with_format("Modèle : ", font_style="italic")
        if self.current_mode.client_manager.client:
            self.console_debug.append_status_with_format(f"{self.current_mode.client_manager.client.get_model_path()}\n", color="green")
        else:
           self.console_debug.append_status_with_format("None\n", color="blue")
        self.console_debug.append_status_with_format("Serveur : ", font_style="italic")
        if check_server_status(self.config.server_ip, self.config.port):
            self.console_debug.append_status_with_format(f"Connected @{self.config.server_ip}:{self.config.port} \n", color="green")
        else:
            self.console_debug.append_status_with_format(f"NOT Connected @{self.config.server_ip}:{self.config.port} \n", color="red")
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
        self.console_debug.append_status_with_format(f"{self.keyboard_shortcut}\n", color="green")

        self.console_debug.append_status_with_format("Debug : ", font_style="italic")
        self.console_debug.append_status_with_format(f"{self.config.debug}\n", color="green")

        self.console_debug.append_status_with_format("Position actuelle de la fenêtre : x=", font_style="italic")
        self.console_debug.append_status_with_format(self.root.winfo_x(), color="green")
        self.console_debug.append_status_with_format(", y=", font_style="italic")
        self.console_debug.append_status_with_format(f"{self.root.winfo_y()}\n", color="green")

        self.console_debug.append_status_with_format("Fichier des insertions : ", font_style="italic")
        self.console_debug.append_status_with_format(get_config_path(self.config.insertions), color="green")


    #---------------------------------------------------------------------------------------------------------------------
#               Fenetre shorcut a détacher dans une autre class 
    def change_shortcut(self):
        self.root.attributes("-topmost", False)  # Désactiver l'attribut "toujours au-dessus"
        self.shortcut_window = tk.Toplevel(self.root)
        self.shortcut_window.title("Changer le raccourci clavier")
        self.shortcut_window.attributes("-topmost", True)  # S'assurer que la fenêtre est au-dessus

        tk.Label(self.shortcut_window, text="Appuyez sur une nouvelle combinaison de touches :").pack(pady=10)
        self.shortcut_entry = tk.Entry(self.shortcut_window)
        self.shortcut_entry.pack(pady=10)
        self.shortcut_entry.bind('<KeyPress>', self.get_shortcut)
        self.shortcut_entry.focus_set()

        # Réinitialiser self.keyboard_shortcut
        self.keyboard_shortcut = ''
        self.shortcut_entry.delete(0, tk.END)

        # Assurez-vous de réactiver "toujours au-dessus" lorsque la fenêtre est fermée
        self.shortcut_window.protocol("WM_DELETE_WINDOW", self.on_close_shortcut_window)


    def on_close_shortcut_window(self):
        self.root.attributes("-topmost", self.current_mode.mode.topmost)  # Réactiver l'attribut "toujours au-dessus"
        self.shortcut_window.destroy()

    def get_shortcut(self, event):
        key = self.map_key_name(event.keysym)

        if key == 'Return':  # Ignore the Enter key itself
            if self.is_valid_shortcut(self.keyboard_shortcut.split('+')):
                keyboard.clear_all_hotkeys()
                keyboard.add_hotkey(self.keyboard_shortcut, self.current_mode.toggle_start_stop)
                self.on_close_shortcut_window()  # Fermer la fenêtre et réactiver "toujours au-dessus"
            else:
                messagebox.showerror("Raccourci invalide", "La combinaison de touches n'est pas valide.")
                self.keyboard_shortcut = ''  # Reset the pressed keys
                self.shortcut_entry.delete(0, tk.END)
            return

        current_keys = self.keyboard_shortcut.split('+') if self.keyboard_shortcut else []

        if key not in current_keys:
            current_keys.append(key)

        self.keyboard_shortcut = '+'.join(current_keys)
        self.shortcut_entry.delete(0, tk.END)
        self.shortcut_entry.insert(0, self.keyboard_shortcut)

        
        
    def is_valid_shortcut(self, keys):
        if len(keys) == 1 and (keys[0].startswith('F') or keys[0] == 'fn'):
            return True  # Touche de fonction seule ou Fn seule
        if len(keys) == 2 and ('ctrl' in keys or 'fn' in keys):
            return True  # Ctrl+quelque chose ou Fn+quelque chose
        if len(keys) == 3 and 'ctrl' in keys and 'shift' in keys:
            return True  # Ctrl+Shift+quelque chose
        if len(keys) == 3 and 'ctrl' in keys and 'alt' in keys:
            return True  # Alt+Ctrl+quelque chose
        if len(keys) == 3 and 'fn' in keys and 'ctrl' in keys:
            return True  # Fn+Ctrl+quelque chose
        if len(keys) == 4 and 'ctrl' in keys and 'alt' in keys and 'shift' in keys:
            return True  # Alt+Ctrl+Shift+quelque chose
        if len(keys) == 4 and 'fn' in keys and 'ctrl' in keys and 'shift' in keys:
            return True  # Fn+Ctrl+Shift+quelque chose
        if len(keys) == 5 and 'fn' in keys and 'ctrl' in keys and 'alt' in keys and 'shift' in keys:
            return True  # Fn+Alt+Ctrl+Shift+quelque chose
        return False


    def map_key_name(self, key):
        key_mapping = {
            'Control_L': 'ctrl',
            'Control_R': 'ctrl',
            'Shift_L': 'shift',
            'Shift_R': 'shift',
            'Alt_L': 'alt',
            'Alt_R': 'alt',
            'Fn_L': 'fn',
            'Fn_R': 'fn',
            # Ajoutez d'autres mappages si nécessaire
        }
        return key_mapping.get(key, key)
#---------------------------------------------------------------------------------------------------------------------


def start_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

def on_resize(event):
        width = event.width
        height = event.height
        print(f"Ma fenêtre Tkinter - Dimensions: {width}x{height}")

if __name__ == "__main__":
     # Récupérer l'ID du processus du splash screen passé en argument
    # if len(sys.argv) > 1:
    #     splash_pid = sys.argv[1]
    #     try:
    #         os.kill(int(splash_pid), signal.SIGTERM)
    #         print(f"Splash screen (PID {splash_pid}) fermé avec succès.")
    #     except Exception as e:
    #         print(f"Erreur lors de la fermeture du splash screen : {e}")
    #         pass
    
    try:
        root = tk.Tk()
        # Create a new event loop
        new_loop = asyncio.new_event_loop()
        threading.Thread(target=start_loop, args=(new_loop,), daemon=True).start()

        app = App(root, new_loop)  # Pass the new loop to the app
        # root.bind("<Configure>", on_resize)
        root.mainloop()
    except Exception as e:
        print(e)