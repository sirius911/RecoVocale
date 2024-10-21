import time
from Mode import Mode
import tkinter as tk
from utils_window import create_menus, create_buttons
from info import DIRECT
from ClientManager import ClientManager
from utils_keyboard import Simulator
from pynput.keyboard import Key


def trouver_bornes_mot_tk(phrase, curseur, direction='left'):
    # Si le curseur est à la fin, on le place au dernier caractère
    if curseur == -1:
        curseur = len(phrase) - 1

    # Assurer que le curseur est dans les bornes de la phrase
    curseur = max(0, min(len(phrase) - 1, curseur))
    
    if direction == 'left':
        # Trouver le début du mot à left
        debut = curseur
        while debut > 0 and phrase[debut].isspace():
            debut -= 1
        while debut > 0 and not phrase[debut - 1].isspace():
            debut -= 1
        
        # Trouver la fin du mot
        fin = curseur
        while fin < len(phrase) and not phrase[fin].isspace():
            fin += 1
        return debut, fin - 1
    
    elif direction == 'right':
        # Trouver le début du mot à right
        debut = curseur
        while debut < len(phrase) and phrase[debut].isspace():
            debut += 1
        
        fin = debut
        while fin < len(phrase) and not phrase[fin].isspace():
            fin += 1
        
        return debut, fin - 1
    
    else:
        raise ValueError("La direction doit être 'left' ou 'right'.")


class Mode_Direct(Mode):
    def enter(self):
        self.mode = DIRECT
        self.mod_var.set(DIRECT)
        self.ui()
        #----------------- Lien Client Whisper -----------------------
        self.client_manager = ClientManager(
            host = self.app.config.server_ip,
            port = self.app.config.port,
            lang = "fr",
            model = "small",
            translate = False,
            use_vad = True,
            save_output_recording = False,
            output_recording_filename = "",
            update_callback = self.update_transcriptions,  # Pass the callback to ClientManager
            insertions = self.app.insertions,
            fenetre_gestion_insertions = self.is_ouverte,
            mode=self.mode,
            nb_repeat=self.app.config.nb_repeat,
        )
        super().enter()
        self.flag_begin = True
        self.pile = ['']
    def ui(self):
        create_menus(self)
        create_buttons(self)

         # Configure the grid system of the root window
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Create the text box frame
        self.text_box_frame = tk.Frame(self.root)
        self.text_box_frame.grid(row=1, column=0, sticky="nsew")

        # Add scrollbar to the text box
        self.text_box_scrollbar = tk.Scrollbar(self.text_box_frame)
        self.text_box_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Add the text box
        self.text_box = tk.Text(self.text_box_frame, yscrollcommand=self.text_box_scrollbar.set)
        self.text_box.pack(fill=tk.BOTH, expand=True)

        # Configure the selection tag
        self.text_box.tag_configure("sel", background="yellow", foreground="black")

        # Attach the scrollbar to the text box
        self.text_box_scrollbar.config(command=self.text_box.yview)

        # Attacher l'événement à la Text box
        self.text_box.bind("<Key>", self.on_text_change)

        # Create the status bar at the bottom of the window
        self.status_bar = tk.Label(self.root, text="Bienvenue dans l'application", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=2, column=0, sticky="ew")

    def pause(self):
        print("Pausing client in Mode Direct")
        super().pause()

    def unpause(self):
        print(f"UnPausing client in Mode Direct")
        super().unpause()

    def stop_client(self):
        print(f"Stop client in Mode Direct")
        super().stop_client()

    def stop(self):
        self.stop_client()

    def valid_transcriptions(self):
        self.stop_client()

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
        print(f"Pile après undo: {self.pile}")

    def get_selected_text(self):
        """
            renvoi le texte selectionné de la TextBox + Flag
            Si aucune selection renvoi toute le text
            le Flag est True si on envoi l'integralité et False si une partie
        """
        try:
            # Vérifie s'il y a une sélection
            if self.text_box.tag_ranges("sel"):
                # Récupère le texte sélectionné
                selected_text = self.text_box.get(tk.SEL_FIRST, tk.SEL_LAST)
                return selected_text, False
            else:
                # si aucune selection on envoi la transcription complète
                return self.transcription.get(), True
        except tk.TclError:
            # Gestion d'erreur si aucune sélection n'est faite
            return self.transcription.get(), True
        
    def get_pos_select(self):
        """
            retourne un couple (start,end) si selection dans text_box ou None 
        """
        try:
            if self.text_box.tag_ranges("sel"):
                # Obtenir les positions 'ligne.colonne' de la sélection
                start = self.text_box.index(tk.SEL_FIRST)
                end = self.text_box.index(tk.SEL_LAST)
                
                # Convertir ces positions en indices globaux
                start_index = self.text_box.count("1.0", start)[0]  # Distance depuis le début du texte
                end_index = self.text_box.count("1.0", end)[0]      # Distance jusqu'à la fin du texte sélectionné
                
                return (start_index, end_index)
            else:
                return (0, 0)
        except tk.TclError:
            return (0, 0)

    def clear_text_box(self):
        """
        Clear the content of the text box.
        """
        time.sleep(0.5)
        self.save_text_box()
        _, all = self.get_selected_text()
        self.valid_transcriptions()
       
        if all:
            self.transcription.clear()
            self.text_box.delete('1.0', tk.END)
        else:
            Simulator([Key.delete])

        self.root.update()

    def get_pos_curseur(self):
        # Utiliser "1.0" comme point de départ et obtenir le nombre total de caractères jusqu'au curseur
        position_globale = self.text_box.count("1.0", "insert", "chars")
        if position_globale:
            return position_globale[0]
        return 0

    def set_pos_curseur(self, position_globale):
        # Utiliser "1.0" comme point de départ et déplacer le curseur à la position globale
        index_ligne_colonne = self.text_box.index(f"1.0 + {position_globale}c")
        
        # Repositionner le curseur à l'index ligne.colonne calculé
        self.text_box.mark_set("insert", index_ligne_colonne)
        
        # S'assurer que le curseur est visible
        self.text_box.see("insert")
    
    def save_text_box(self):
        # Sauvegarder uniquement si le texte a changé
        text_box = self.text_box.get("1.0", tk.END).strip()
        if not self.pile or text_box != self.pile[-1]:
            self.pile.append(text_box)
            self.edit_menu.entryconfig(0, state='normal')
            print("État sauvegardé:", self.pile)

    def on_text_change(self, event):
        if event and (event.keysym in ("Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R") or
                      (event.state & 0x4 and event.keysym == "z")):
            return
        self.save_text_box()
        self.transcription.set(self.text_box.get("1.0", tk.END).strip())
        self.transcription.pos_cur = self.get_pos_curseur()
        

    def update_transcriptions(self, message, ending):
        if self.flag_begin:
            self.flag_begin = False
            self.transcription.pos_cur = self.get_pos_curseur()
            self.transcription.cur_selec = self.get_pos_select()
            self.save_text_box()

        self.transcription.update(message)

        self.text_box.delete('1.0', tk.END)
        self.text_box.insert(tk.END, self.transcription.text_box_en_cours)
        if ending:
            self.flag_begin = True
            self.transcription.validation()
            self.set_pos_curseur(self.transcription.fin_insertion)
        else:
            self.set_pos_curseur(self.transcription.pos_cur)

    def copy_to_clipboard(self):
        self.status_bar.config(text='- Copie -', bg='lightblue', fg='darkblue', anchor=tk.CENTER)
        self.root.clipboard_clear()
        self.root.clipboard_append(self.get_selected_text()[0])
        time.sleep(0.5)
        self._update_barre_status()

    def select_text_box(self, dir = "left"):
        self.text_box.focus_set()
        # Effacer la sélection actuelle (retirer la surbrillance)
        self.text_box.tag_remove("sel", "1.0", tk.END)


        # Récupérer la position du curseur dans la text_box
        cursor_index = self.text_box.index(tk.INSERT)   

        # Convertir cet index en offset numérique (compter les caractères depuis le début)
        line, column = map(int, cursor_index.split('.'))
        # print(f"cursor_index = ({line},{column})")
        if dir == "left":
            column -= 1
        else:
            column += 1
        # print(f"next cursor index = ({line},{column})")    
        current_position = int(self.text_box.index(f"{line}.0+{column}c").split('.')[1])

        # Récupérer tout le texte du text_box
        full_text =self.text_box.get("1.0", tk.END)
        
        # Trouver les bornes du mot à left ou à right
        start_pos, end_pos = trouver_bornes_mot_tk(full_text, current_position, dir)
        
        # Convertir ces bornes en indices Tkinter
        start_index = f"{line}.0+{start_pos}c"
        end_index = f"{line}.0+{end_pos + 1}c"  # Incrémenter pour inclure la dernière lettre
        # print(f"start_index = {start_index}, end_index = {end_index}")
        # Sélectionner le mot dans la text_box
        self.text_box.tag_add("sel", start_index, end_index)

        # Mettre le curseur à la fin ou au début  de la sélection
        if dir == "left":
            self.text_box.mark_set(tk.INSERT, start_index)
        else:
            self.text_box.mark_set(tk.INSERT, end_index)
        self.text_box.see(tk.INSERT)  # Faire défiler jusqu'au curseur

    def exit(self):
        retour = self.text_box.get("1.0", tk.END) # on retourne la transcription en cours
        super().exit()
        return retour