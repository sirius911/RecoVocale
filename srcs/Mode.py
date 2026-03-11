# from utils_socket import check_server_status
import string
import time
from info import *
from Transcription import Transcription
import tkinter as tk
from insertions import FenetreGestion
import enchant

class Mode:
    def __init__(self, app):
        self.app = app
        self.root = app.root
        self.mod_var = tk.StringVar()
        self.transcription = Transcription()
        self.fenetre_gestion_ouverte = False  # Attribut pour savoir si la fenêtre est ouverte
        self.simulator_keyboard = None
        self.transcription_en_cours = False

        # # Définir le chemin du répertoire de configuration dans %APPDATA%\RecoVocale
        # config_dir = os.path.join(os.getenv('APPDATA'), 'RecoVocale')
        # path_to_dic = os.path.join(config_dir, "fr.dic")
        # path_to_aff = os.path.join(config_dir, "fr.aff")
        self.dico = enchant.Dict("fr_FR")
        self.mots_personnels = set()
        # self.dico = SpellChecker(language="fr")
        # self.dico.word_frequency.add("cardiopathie")
        self.enter()

    def enter(self):
        self.root.resizable(self.mode.resizable, self.mode.resizable)
        self.root.attributes("-topmost", self.mode.topmost)
        self.root.geometry(f"{self.mode.window_width}x{self.mode.window_height}+{self.app.config.x_window}+{self.app.config.y_window}")
        if self.mode == REDUIT:
            self.root.title(f"RV v{VERSION}")
        else:
            self.root.title(f"RecoVocale [{self.app.config.server_ip}:{self.app.config.port}] (v{VERSION}) {"" if self.app.status_server else "not"} connected")

    def get_selected_text(self):
        return self.transcription.get()
    
    def valid_transcriptions(self):
        self.stop_client()
    
    def stop_client(self):
        self.transcription.validation()
        if self.client_manager:
            self.client_manager.stop_client()
        self.app.recording = False
        self.update()

    def copy_to_clipboard(self):
        self.status_bar.config(text='- Copie -', bg='lightblue', fg='darkblue', anchor=tk.CENTER)
        self.root.clipboard_clear()
        self.root.clipboard_append(self.transcription.get())
        time.sleep(0.5)
        self._update_barre_status()

    def pause(self):
        self.client_manager.pause()
        self.app.recording = False
        self.update()

    def unpause(self):
        if self.app.status_server == True:
            if not self.app.recording:
                if self.client_manager.client:
                    self.client_manager.client.set_pause(False)
                else:
                    self.client_manager.start_client(self.app.loop)
                self.app.recording = True
        self.update()

    def exit_app(self):
        # self.icon.stop()
        self.app.on_closing()

    def _update_rec_circle(self):
        fill = 'red' if self.app.recording else 'grey'
        self.rec_canvas.itemconfig(self.rec_circle, fill=fill)

    def _update_image_button(self):
        if self.app.recording:
            self.rec_button.config(image=self.pause_image)
        else:
            self.rec_button.config(image=self.record_image)

    def _update_barre_status(self):
        if self.mode == REDUIT:
            message = f"RecoVocale {VERSION}"
        else:
            message = f"RecoVocale [{self.app.config.server_ip}:{self.app.config.port}] (v{VERSION}) {"" if self.app.status_server else "not"} connected"

        if self.app.status_server == False:
            self.status_bar.config(text=message, fg='red', anchor=tk.W)
        elif self.app.recording:
            self.status_bar.config(text="RECORDING ...", fg='black', bg='red', anchor=tk.CENTER)
        elif self.transcription_en_cours:
            self.status_bar.config(text="Transcription ...en cours", bg='lightblue', fg='darkblue', anchor=tk.W)
        else:
            self.status_bar.config(text=message, bg='lightblue', fg='darkblue', anchor=tk.W)

    def update(self):
        self._update_rec_circle()
        self._update_image_button()
        self._update_barre_status()
        # self.app.info()

    def name(self):
        return self.mode.name
    
    def select_text_box(self, dir = "left"):
        pass

    def undo(self, event=None):
        if event and event.keysym in ("Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R") :
            return
        if self.pile:
            dernier_etat = self.pile.pop()
            self.text_box.delete('1.0', tk.END)
            self.text_box.insert('1.0', dernier_etat)
            self.transcription.set(dernier_etat)
        if not self.pile:
            self.pile = ['']
            self.edit_menu.entryconfig(0, state='disabled')
    
    def toggle_start_stop(self):
        """
        Toggle the start/stop state of the transcription client.
        """
        if self.app.recording:
            self.pause()
        else:
            self.unpause()

    def toggle_debug(self):
        #maj de la variable config
        self.app.config.debug = self.debug_var.get()
        if self.app.config.debug:
            self.app.console_debug.debug_window.deiconify()
        else:
            self.app.console_debug.debug_window.withdraw()

    def toggle_dictionnaire(self):
        #maj de la variable config
        self.app.config.dictionnaire = self.dico_var.get()
        if self.text_box:
            self.verification_dico()

    def exit(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        # return self.transcription.get() # on retourne la transcription en cours

    def ouvrir_gestion_insertions(self):
        """Ouvre la fenêtre de gestion des insertions"""
        if not self.fenetre_gestion_ouverte:
            self.fenetre_gestion = FenetreGestion(self.root, self.app.insertions, self.fermer_gestion_insertions)
            self.fenetre_gestion.protocol("WM_DELETE_WINDOW", self.fermer_gestion_insertions)
            self.fenetre_gestion_ouverte = True

    def fermer_gestion_insertions(self):
        """Méthode appelée lorsque la fenêtre de gestion est fermée"""
        if self.fenetre_gestion:
            self.fenetre_gestion.destroy()
        self.fenetre_gestion_ouverte = False

    def save_text_box(self):
        if self.text_box:
            # Sauvegarder uniquement si le texte a changé
            text_box = self.text_box.get("1.0", tk.END).rstrip('\n')
            if not self.pile or text_box != self.pile[-1]:
                self.pile.append(text_box)
                self.edit_menu.entryconfig(0, state='normal')
                # print("État sauvegardé:", self.pile)

    def on_text_change(self, event):
        if event and (event.keysym in ("Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R") or
                      (event.state & 0x4 and event.keysym == "z")):
            return
        self.save_text_box()
        self.root.after_idle(self.text_change) # pour attendre que tkinter est bien écrit les modifications

    def text_change(self): 
        self.trash_button.config(state=tk.NORMAL)   
        nouveau_text = self.text_box.get("1.0", tk.END)
        # self.save_text_box()
        self.transcription.set(nouveau_text)
        self.transcription.text_box_en_cours = nouveau_text
        self.transcription.pos_cur = self.get_pos_curseur()
        self.verification_dico()

    def verification_dico(self):
        #efface les marquages précédents
        self.text_box.tag_remove("incorrect", "1.0", tk.END)
        if not self.app.config.dictionnaire:
            return

        # Séparer le contenu en mots
        contenu = self.text_box.get("1.0", tk.END)
        mots = contenu.split()
        
        for mot in mots:
            # Nettoyer le mot de la ponctuation en début et fin, sans modifier l'original
            mot_nettoye = mot.strip(string.punctuation)

            # Vérifier chaque mot
            if mot_nettoye and not self.dico.check(mot_nettoye):
                # Trouver les positions du mot
                start_idx = contenu.find(mot)
                end_idx = start_idx + len(mot)
                # Convertir les positions en indices tkinter
                start = f"1.0 + {start_idx} chars"
                end = f"1.0 + {end_idx} chars"
                # Ajouter une balise pour souligner les mots incorrects
                self.text_box.tag_add("incorrect", start, end)
                # Afficher les suggestions (affichage simplifié)
                # print(f"{mot} est incorrect. Suggestions : {self.dico.suggest(mot)}")

    def show_context_menu(self, event):
        print(self.mots_personnels)
        # Obtenir l'index du clic droit
        index = self.text_box.index(f"@{event.x},{event.y}")
        
        # Récupérer le mot sous le curseur
        word_start = self.text_box.index(f"{index} wordstart")
        word_end = self.text_box.index(f"{index} wordend")
        incorrect_word = self.text_box.get(word_start, word_end)

        # Vérifier si le mot est incorrect et obtenir des suggestions
        if not self.dico.check(incorrect_word):
            suggestions = self.dico.suggest(incorrect_word)

            personnalise_suggestions = [
                s for s in suggestions if s in self.mots_personnels
            ]
            autres_suggestions = [
                s for s in suggestions if s not in self.mots_personnels
            ]
            suggestions = personnalise_suggestions + autres_suggestions

            # Effacer le menu précédent et ajouter les nouvelles suggestions
            self.context_menu.delete(0, tk.END)
            for suggestion in suggestions:
                self.context_menu.add_command(
                    label=suggestion,
                    command=lambda s=suggestion, ws=word_start, we=word_end: self.replace_word(s, ws, we)
                )
            self.context_menu.add_separator()
            self.context_menu.add_command(
                label="Ajouter au dictionnaire",
                command=lambda:self.ajouter_mot_personnalise(incorrect_word)
            )
            self.context_menu.post(event.x_root, event.y_root)

    def replace_word(self, suggestion, word_start, word_end):
        self.save_text_box()
        # Remplacer le mot dans la text box
        self.text_box.delete(word_start, word_end)
        self.text_box.insert(word_start, suggestion)
        # Retirer le marquage incorrect
        self.text_box.tag_remove("incorrect", word_start, word_end)

    def ajouter_mot_personnalise(self, mot):
        self.mots_personnels.add(mot)
        self.dico.add(mot)
        # with open("chemin/vers/mots_personnels.txt", "a") as f:
            # f.write(mot + "\n")

    def is_ouverte(self):
        return self.fenetre_gestion_ouverte
    
    def clear_text_box(self):
        pass