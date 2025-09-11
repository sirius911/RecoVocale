import tkinter as tk
import tkinter.font as tkFont
from Mode import Mode
from utils_window import create_buttons, update_status_bar
from menus import create_menus
from info import DIRECT
from utils_keyboard import Simulator
from pynput.keyboard import Key
from clipboard import set_clipboard
# from Correcteur import intercept, corrige_ponctuation
# from mydict_corrector import correct_with_dict


class Mode_Direct(Mode):
    """
    Mode d’utilisation direct pour l'application RecoVocale.

    Permet une transcription immédiate à partir du micro ou d’un fichier audio,
    avec affichage en temps réel dans une zone de texte. Ce mode gère aussi la
    vérification orthographique, les insertions, les raccourcis clavier et les interactions utilisateur.

    Hérite de la classe `Mode` pour les fonctionnalités communes.
    """
    def __init__(self, app, mode=DIRECT):
        super().__init__(app, mode)
        self.transcription_interrompue = False
        self.enter()

    def ui(self) -> None:
        """
        Construit l’interface utilisateur spécifique au mode direct :
        menus, boutons, zone de texte, barre de statut, gestion des événements clavier et clic droit.
        """

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
        self.text_box = tk.Text(self.text_box_frame, yscrollcommand=self.text_box_scrollbar.set, wrap='word')
        self.text_box.pack(fill=tk.BOTH, expand=True)
        # Définir la police
        font = tkFont.Font(family="Calibri", size=12)
        self.text_box.configure(font=font)

        # balise pour les mots incorrects
        self.text_box.tag_config("incorrect", foreground="red", underline=True)
        # self.text_box.config(state=tk.DISABLED)

        # Configure the selection tag
        self.text_box.tag_configure("sel", background="yellow", foreground="black")

        # Attach the scrollbar to the text box
        self.text_box_scrollbar.config(command=self.text_box.yview)

        # Attacher l'événement à la Text box
        self.text_box.bind("<Key>", self.on_text_change)

        # self.text_box.bind("<Button-3>", self.show_context_menu)
        # # Création du menu contextuel
        # self.context_menu = tk.Menu(self.root, tearoff=0)

        # Create the status bar at the bottom of the window
        self.status_bar = tk.Label(self.root, text="Bienvenue dans l'application", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=2, column=0, sticky="ew")

    def unpause(self, audio_file: str | None = None):
        if self.app.recording or self.vt.is_recording or not self.app.status_server:
            return
        try:
            self.vt.start()
            self.app.recording = True

            def _ui_ok():
                self.text_box.config(state=tk.NORMAL)
                self.status_bar.config(text="* Enregistrement… *", bg="red", fg="darkblue", anchor=tk.CENTER)
                self._update_rec_circle()
                self._update_image_button()

            self.add_to_ui_queue(_ui_ok)

        except Exception as e:
            def _ui_err(e):
                self.status_bar.config(
                    text=f"Erreur start micro: {e}",
                    bg="lightblue", fg="darkblue", anchor=tk.W
                )

            self.add_to_ui_queue(_ui_err, e)

    def pause(self):
        if not self.app.recording and not self.vt.is_recording:
            return
        try:
            texte = self.vt.stop()  # transcription finale d’un seul tenant
        except Exception as e:
            update_status_bar(status_bar=self.status_bar, text=f"Erreur stop/transcription: {e}",
                              bg="lightblue", fg="darkblue", anchor=tk.W)
            texte = ""
        finally:
            self.app.recording = False

        if texte and texte.strip():
            self.handle_final_text(texte)

        def _maj():
            if texte and texte.strip():
                self.trash_button.config(state=tk.NORMAL)
            self._update_rec_circle()
            self._update_image_button()

        self.add_to_ui_queue(_maj)
        update_status_bar(status_bar=self.status_bar, text="Segment ajouté",
                          bg='lightblue', fg='darkblue', anchor=tk.W)

    def stop(self) -> None:
        # Si on utilise VT et qu’on enregistre, faire une pause (récupère et insère)
        if hasattr(self, "vt") and (self.vt.is_recording or self.app.recording):
            self.pause()
            return

    def on_record_start(self):
        # UI rouge pendant l’enregistrement
        self.text_box.config(state=tk.NORMAL)
        update_status_bar(status_bar=self.status_bar, text="* Enregistrement… *",
                          bg='red', fg='darkblue', anchor=tk.CENTER)

    def handle_final_text(self, text: str):
        txt = super().handle_final_text(text)

        if hasattr(self, "save_text_box"):
            self.save_text_box()

        # Insérer au curseur (remplacer la sélection si présente)
        def _insert_final(t=txt):
            if self.text_box.tag_ranges("sel"):
                self.text_box.delete(tk.SEL_FIRST, tk.SEL_LAST)
            self.text_box.insert("insert", t + " ")
            self.text_box.see("insert")
            self.root.update_idletasks()
            self.log(text)
        if not self.is_ouverte():
            self.add_to_ui_queue(_insert_final)

    def save_text_box(self) -> None:
        """
        Sauvegarde le contenu actuel du champ texte dans la pile d'annulation.
        """

        if self.text_box:
            # Sauvegarder uniquement si le texte a changé
            text_box = self.text_box.get("1.0", tk.END).rstrip('\n')
            if not self.pile or text_box != self.pile[-1]:
                self.pile.append(text_box)
                self.edit_menu.entryconfig(0, state='normal')
                # print("État sauvegardé:", self.pile)

    def get_selected_text(self) -> tuple[str, bool]:
        """
        Récupère le texte sélectionné dans la zone de texte.

        Returns:
            tuple[str, bool]: Le texte sélectionné ou tout le texte si rien n'est sélectionné,
                            et un booléen indiquant si tout le texte est retourné.
        """

        try:
            # Vérifie s'il y a une sélection
            if self.text_box.tag_ranges("sel"):
                # Récupère le texte sélectionné
                selected_text = self.text_box.get(tk.SEL_FIRST, tk.SEL_LAST)
                return selected_text, False
            else:
                # si aucune selection on envoi la transcription complète
                selected_text = self.text_box.get("1.0", tk.END)
                return selected_text, True
        except tk.TclError:
            # Gestion d'erreur si aucune sélection n'est faite
            selected_text = self.text_box.get("1.0", tk.END)
            return selected_text, True

    def get_pos_select(self) -> tuple[int, int]:
        """
        Récupère les indices globaux de début et fin de la sélection texte.

        Returns:
            tuple[int, int]: (start, end) ou (0, 0) si rien n'est sélectionné.
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

    def clear_text_box(self) -> None:
        """
        Efface le texte sélectionné ou tout le texte s’il n’y a pas de sélection.
        """

        self.save_text_box()
        _, all = self.get_selected_text()

        def clear():
            self.text_box.config(state=tk.NORMAL)
            if all:
                self.text_box.delete('1.0', tk.END)
            else:
                Simulator([Key.delete])

        self.add_to_ui_queue(clear)
        # self.root.update()

    def get_pos_curseur(self) -> int:
        """
        Récupère la position du curseur dans la zone de texte.

        Returns:
            int: Position globale en nombre de caractères.
        """

        # Utiliser "1.0" comme point de départ et obtenir le nombre total de caractères jusqu'au curseur
        position_globale = self.text_box.count("1.0", "insert", "chars")
        if position_globale:
            return position_globale[0]
        return 0

    def set_pos_curseur(self, position_globale: int) -> None:
        """
        Déplace le curseur à une position donnée dans la zone de texte.

        Args:
            position_globale (int): Position souhaitée en caractères depuis le début.
        """
        def set_cursor():
            # Utiliser "1.0" comme point de départ et déplacer le curseur à la position globale
            index_ligne_colonne = self.text_box.index(f"1.0 + {position_globale}c")

            # Repositionner le curseur à l'index ligne.colonne calculé
            self.text_box.mark_set("insert", index_ligne_colonne)

            # S'assurer que le curseur est visible
            self.text_box.see("insert")

        self.add_to_ui_queue(set_cursor)

    def copy_to_clipboard(self) -> None:
        """
        Copie le texte sélectionné (ou tout le texte) dans le presse-papier.
        """
        def copy():
            self.status_bar.config(text='- Copie -', bg='lightblue', fg='darkblue', anchor=tk.CENTER)
            set_clipboard(text=self.get_selected_text()[0])
            # self.root.clipboard_clear()
            # self.root.clipboard_append(self.get_selected_text()[0])

        self.add_to_ui_queue(copy)

    def on_text_change(self, event) -> None:
        """
        Gère les changements dans le champ texte. Ignore certaines touches de contrôle.

        Args:
            event: Événement clavier de Tkinter.
        """

        if event and (event.keysym in ("Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R") or
                      (event.state & 0x4 and event.keysym == "z")):
            return
        self.save_text_box()
        self.root.after_idle(self.text_change)  # pour attendre que tkinter est bien écrit les modifications

    def text_change(self) -> None:
        """
        Applique les changements de texte et met à jour la transcription et le curseur.
        """
        def apply_changes():
            self.trash_button.config(state=tk.NORMAL)
            self.save_text_box()

        self.add_to_ui_queue(apply_changes)

    def exit(self) -> str:
        """
        Ferme proprement la fenêtre du mode et retourne le texte courant.
        """
        retour = ""
        try:
            if hasattr(self, "text_box") and self.text_box.winfo_exists():
                retour = self.text_box.get("1.0", tk.END).rstrip("\n")
        except tk.TclError:
            retour = ""

        super().exit()
        return retour
