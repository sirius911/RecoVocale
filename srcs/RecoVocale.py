import tkinter as tk
from tkinter import messagebox
import asyncio
import threading
import keyboard

from UserConfig import UserConfig
from Direct_Mode import Direct_Mode
from Record_Mode import Record_Mode
from utils_socket import check_server_status
from utils_keyboard import Simulator
from Micro import Micro
from info import *
# from ClientManager import ClientManager
# from Transcription import Transcription

class App:
    def __init__(self, root, loop):
        self.config = UserConfig()
        mode = self.config.mode
        self.root = root
        self.recording = False
        # self.root.title(f"RecoVocale [{self.config.server_ip}:{self.config.port}] (v{VERSION})")
        self.root.attributes("-topmost", True)  # Keep the window on top of others
 
        #-------------------check serveur-----------------------
        self.status_server = check_server_status(self.config.server_ip, self.config.port)
        self.root.title(f"RecoVocale [{self.config.server_ip}:{self.config.port}] (v{VERSION}) {"" if self.status_server else "not"} connected")
        #-----------------Shortcut------------------------------
        self.keyboard_shortcut = self.config.shortcut
        #----------------------MODE----------------------------
        print(f"mode = {mode}")
        if mode == "RECORD":
            self.current_mode = Record_Mode(self)
            # self.client_manager = None
        else:
            self.current_mode = Direct_Mode(self)

        self.simulate_keyboard = False
        self.simulator_keyboard = Simulator(text=None, debug=self.config.debug)
        keyboard.add_hotkey(self.keyboard_shortcut, self.current_mode.toggle_start_stop)

        # Use the provided asyncio event loop
        self.loop = loop

        self.root.protocol("WM_DELETE_WINDOW", self.current_mode.exit_app)

        # #---------------------------MICRO----------------------------
        # Initialize the microphone 
        self.mic = Micro(loop, app=self.current_mode)

        self.current_mode.start()

    def paste_from_clipboard(self):
        Simulator('\u0001v')
            
    def running(self):
        return self.client_manager.running

    def update(self):
        if self.current_mode:
            self.current_mode.update() 

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
        self.root.quit()
        self.loop.stop()

    def switch_mode(self, mode):
        print(f"switch_mode({mode.name})")
        if self.current_mode:
            if self.current_mode.mode != mode:
                self.current_mode.stop()
                self.current_mode.exit()
                self.current_mode = None
                if mode == DIRECT:
                    self.current_mode = Direct_Mode(self)
                elif mode == RECORD:
                    self.current_mode = Record_Mode(self)
                else:
                    print("Erreur de Mode dans App")
                    self.on_closing()
                self.current_mode.start()
                # self.current_mode.update()
                # Utiliser after_idle pour s'assurer que geometry est bien appliqué
                self.root.after_idle(lambda: self.root.geometry(f"{self.current_mode.mode.window_width}x{self.current_mode.mode.window_height}+{self.config.x_window}+{self.config.y_window}"))
                self.mic.change_mode(self.current_mode)
                keyboard.clear_all_hotkeys()
                keyboard.add_hotkey(self.keyboard_shortcut, self.current_mode.toggle_start_stop)
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
                # self.start_button.config(text=f"Start ({self.keyboard_shortcut})")
                # self.stop_button.config(text=f"Stop ({self.keyboard_shortcut})")
                # self.icon.title = f"RecoVocale (v{VERSION})[{self.keyboard_shortcut}]"
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

# def on_resize(event):
#         # Afficher les dimensions de la fenêtre dans la barre de titre
#         width = event.width
#         height = event.height
#         print(f"Ma fenêtre Tkinter - Dimensions: {width}x{height}")

if __name__ == "__main__":
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