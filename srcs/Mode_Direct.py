import time
import tkinter as tk
import tkinter.font as tkFont
from Mode import Mode
from utils_window import create_menus, create_buttons
from info import DIRECT
from utils_keyboard import Simulator
from pynput.keyboard import Key


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

        self.text_box.bind("<Button-3>", self.show_context_menu)
        # Création du menu contextuel
        self.context_menu = tk.Menu(self.root, tearoff=0)

        # Create the status bar at the bottom of the window
        self.status_bar = tk.Label(self.root, text="Bienvenue dans l'application", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=2, column=0, sticky="ew")

    def stop(self) -> None:
        """
        Stoppe la transcription, active les boutons,
        repositionne le curseur et vérifie l’orthographe du texte.
        """

        print("Stop() dans Mode Direct", flush=True)
        self.stop_client()
        self.engine.wait_transcription_en_cours(2.0)
        self.engine.clear_transcriptions()
        self.engine.merge()
        self.running_thread = False
        self.text_box.config(state=tk.NORMAL)
        self.trash_button.config(state=tk.NORMAL)
        self.rec_button.config(state=tk.NORMAL)
        self.transcription_en_cours = False
        self.transcription.validation()
        self.set_pos_curseur(self.transcription.fin_insertion)
        self.status_bar.config(text="Transcription ...interrompue", bg='lightblue', fg='darkblue', anchor=tk.W)
        self.transcription_interrompue = True
        self.verification_dico(True)

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
                return self.engine.texte_merge, True
        except tk.TclError:
            # Gestion d'erreur si aucune sélection n'est faite
            return self.engine.texte_merge, True

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
        time.sleep(0.5)
        self.save_text_box()
        _, all = self.get_selected_text()

        self.text_box.config(state=tk.NORMAL)
        if all:

            self.engine.clear()
            self.text_box.delete('1.0', tk.END)
        else:
            Simulator([Key.delete])

        self.root.update()

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
        # Utiliser "1.0" comme point de départ et déplacer le curseur à la position globale
        index_ligne_colonne = self.text_box.index(f"1.0 + {position_globale}c")

        # Repositionner le curseur à l'index ligne.colonne calculé
        self.text_box.mark_set("insert", index_ligne_colonne)

        # S'assurer que le curseur est visible
        self.text_box.see("insert")

    def write_text_box(self, texte):
        if self.text_box:
            self.text_box.config(state=tk.NORMAL)
            self.text_box.delete('1.0', tk.END)
            self.text_box.insert(tk.END, texte)
            self.text_box.config(state=tk.DISABLED)
        else:
            print("Pas de TextBox")

    def update_text_box(self):
        texte = self.engine.get(insertions=self.app.insertions,
                                dico=self.app.config.dictionnaire)
        self.write_text_box(texte)

    def start_transcription_loop(self):
        """
        Thread de transcription qui affiche les segments partiels et colle les segments complets.
        """
        self.running_thread = True
        self.trash_button.config(state=tk.DISABLED)
        # pos_cur = self.get_pos_curseur()
        # pos_selct = self.get_pos_select()
        self.save_text_box()
        while True:
            self.app.recording = self.engine.is_capturing()
            if not hasattr(self, "text_box") or not self.text_box.winfo_exists():
                return  # Le widget a été détruit
            try:

                self.update_text_box()
                if (self.engine.is_transcription_terminee() and not self.app.recording) or not self.running_thread:
                    break

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[Mode_Direct] Erreur dans le thread : {e}")

            # time.sleep(0.1)
        print("Fin du Thread Mode Direct avec is_transcription_terminée() =", self.engine.is_transcription_terminee())
        # essais si la transcription n'est pas terminéee on attend
        start = time.time()
        while not self.engine.is_transcription_terminee():

            self.status_bar.config(text='Attente fin de transcription...',
                                   bg='lightblue', fg='darkblue', anchor=tk.CENTER)
            self.update_text_box()
            if (time.time()-start) > 1.5:
                print("Timeout dans le thread de transcription, on sort")
                break
        self.running_thread = False
        self.trash_button.config(state=tk.NORMAL)
        self.rec_button.config(state=tk.NORMAL)
        # self.engine.print_all_segments()
        # self.update_text_box()
        self.text_box.config(state=tk.NORMAL)
        self.log(nb_mots=self.engine.get_nb_mots_trancripts())

    def copy_to_clipboard(self) -> None:
        """
        Copie le texte sélectionné (ou tout le texte) dans le presse-papier.
        """

        self.status_bar.config(text='- Copie -', bg='lightblue', fg='darkblue', anchor=tk.CENTER)
        self.root.clipboard_clear()
        self.root.clipboard_append(self.get_selected_text()[0])
        time.sleep(0.5)
        self._update_barre_status()

    def exit(self) -> str:
        """
        Ferme proprement la fenêtre du mode et retourne le texte courant.

        Returns:
            str: Texte actuellement dans la zone de transcription.
        """
        retour = self.text_box.get("1.0", tk.END).rstrip("\n")  # on retourne la transcription en cours
        super().exit()
        return retour
