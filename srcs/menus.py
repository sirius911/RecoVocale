import tkinter as tk
from tkinter import BooleanVar
from info import DIRECT, REDUIT, APPRENTI, FICHIER


def toggle_menu_gestion_fenetre(self, state):
    def _maj():
        self.settings_menu.entryconfig("Gestion des Insertions", state=state)
        self.dico_menu.entryconfig("Gérer le dictionnaire personnalisé…", state=state)
    self.add_to_ui_queue(_maj)


def create_menus(self) -> None:
    """
    Crée la barre de menus principale.

    - Paramètres (raccourcis, service, etc.)
    - Mode  (Direct, Réduit, Apprentissage, Transcription…)
    - Édition (copier, coller, undo…)
    """

    # Barre de menus principale
    self.menu_bar = tk.Menu(self.root)
    self.root.config(menu=self.menu_bar)

    # =========================
    # 1. Paramètres
    # =========================
    self.settings_menu = tk.Menu(self.menu_bar, tearoff=0)
    self.menu_bar.add_cascade(label="Paramètres", menu=self.settings_menu)

    # — Raccourci clavier
    self.settings_menu.add_command(label="Raccourcis Clavier",
                                   command=self.app.change_shortcut)

    # — Service
    self.service_var = tk.StringVar(value=self.app.config.service)
    self.service_menu = tk.Menu(self.settings_menu, tearoff=0)
    self.settings_menu.add_cascade(label="Services", menu=self.service_menu)
    self.settings_menu.entryconfig("Services", state="disabled")
    for service in self.app.config.get_services():
        self.service_menu.add_radiobutton(label=service,
                                          variable=self.service_var,
                                          value=service,
                                          command=lambda s=service: self.set_service(s))

    # — Divers
    self.settings_menu.add_separator()
    self.play_audio_var = BooleanVar(value=self.app.config.play_audio)
    self.settings_menu.add_checkbutton(label="Lecture audio locale",
                                       variable=self.play_audio_var,
                                       command=self.toggle_play_audio)

    self.settings_menu.add_separator()
    self.settings_menu.add_command(label="Gestion des Insertions",
                                   command=self.ouvrir_gestion_insertions)
    self.settings_menu.add_separator()

    self.debug_var = BooleanVar(value=self.app.config.debug)
    self.settings_menu.add_checkbutton(label="Debug", variable=self.debug_var,
                                       command=self.toggle_debug)
    self.dico_var = BooleanVar(value=self.app.config.dictionnaire)

    # --- NOUVEAU : sous-menu Dictionnaire
    self.dico_menu = tk.Menu(self.settings_menu, tearoff=0)
    self.settings_menu.add_cascade(label="Dictionnaire", menu=self.dico_menu)

    # Correcteur personnalisé (my.dic)
    self.mydict_var = BooleanVar(value=self.app.config.dictionnaire)
    self.dico_menu.add_checkbutton(
        label="Activer correcteur personnalisé (my.dic)",
        variable=self.mydict_var,
        command=self.toggle_mydict_corrector
    )
    self.dico_menu.add_command(
        label="Gérer le dictionnaire personnalisé…",
        command=self.ouvrir_mydict_editor
    )

    self.settings_menu.add_separator()
    self.settings_menu.add_command(label="Quitter", command=self.app.on_closing)

    # =========================
    # 2. Édition
    # =========================
    self.edit_menu = tk.Menu(self.menu_bar, tearoff=False)
    self.menu_bar.add_cascade(label="Édition", menu=self.edit_menu)

    # — Undo
    self.undo_menu = self.edit_menu.add_command(label="Undo (Ctrl+Z)",
                                                command=self.undo)
    self.root.bind_all("<Control-z>", self.undo)
    self.edit_menu.entryconfig(0, state='disabled')

    # — Copier / Coller
    self.edit_menu.add_separator()
    self.edit_menu.add_command(label="Copier (Ctrl+C)",
                               command=self.copy_to_clipboard)
    self.edit_menu.add_command(label="Coller (Ctrl+V)",
                               command=self.app.paste_from_clipboard)

    # — Effacer (seulement en mode Direct)
    if self.mode == DIRECT:
        self.edit_menu.add_command(label="Effacer",
                                   command=self.clear_text_box)

    if self.mode == REDUIT:
        self.edit_menu.add_separator
        self.word_space_var = BooleanVar(value=self.app.config.word_space)
        self.edit_menu.add_checkbutton(label="Espace avant ", variable=self.word_space_var,
                                       command=self.toggle_word_space)

    # =========================
    # 3. Mode  (NOUVEAU menu racine)
    # =========================
    self.mod_var = tk.StringVar(value=self.mode)
    self.mode_menu = tk.Menu(self.menu_bar, tearoff=0)    # ← nouveau
    self.menu_bar.add_cascade(label="Mode", menu=self.mode_menu)  # ← nouveau

    self.mode_menu.add_radiobutton(label='Direct',
                                   variable=self.mod_var,
                                   value=DIRECT,
                                   command=lambda: self.app.switch_mode(DIRECT))
    self.mode_menu.add_radiobutton(label='Réduit',
                                   variable=self.mod_var,
                                   value=REDUIT,
                                   command=lambda: self.app.switch_mode(REDUIT))
    self.mode_menu.add_radiobutton(label='Apprentissage',
                                   variable=self.mod_var,
                                   value=APPRENTI,
                                   command=lambda: self.app.switch_mode(APPRENTI))
    self.mode_menu.add_radiobutton(label='Transcription Fichiers Audios',
                                   variable=self.mod_var,
                                   value=FICHIER,
                                   command=lambda: self.app.switch_mode(FICHIER))
    self.mode_menu.entryconfig(3, state='disabled')

    # =========================
    # 4. VLC
    # =========================
    # État « Utiliser VLC » – vrai ou faux
    self.vlc_var = tk.BooleanVar(value=getattr(self.app.config, "use_vlc", False))

    # Menu racine « VLC »
    self.vlc_menu = tk.Menu(self.menu_bar, tearoff=0)
    self.menu_bar.add_cascade(label="VLC", menu=self.vlc_menu)

    # Case à cocher « Utiliser VLC »
    self.vlc_menu.add_checkbutton(
        label="Utiliser VLC",
        variable=self.vlc_var,
        onvalue=True,
        offvalue=False,
        command=None,
        state='disabled'
    )

    # Lancer VLC
    self.vlc_menu.add_command(label="Charger un fichier avec VLC", command=self.lance_vlc)
