from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional

# RecoVocale utils
from insertions import GestionnaireInsertion


class FenetreInsertions(tk.Toplevel):
    """
    Éditeur d'insertions simple et robuste (façon mydict_editor).

    Principes :
      - Trois modes clairs : 'view' (lecture), 'edit' (édition d'une sélection), 'new' (création).
      - Détection fiable des modifications (StringVar + <<Modified>> sur Text).
      - Fermeture : propose d'enregistrer les changements (y compris création en cours).
      - Pas de parcours récursif de widgets ; on garde des références directes aux champs.
    """

    def __init__(self, master: tk.Misc, insertions_xml: str = "", termine=None) -> None:
        super().__init__(master)
        self.fonction_termine = termine
        self.title(insertions_xml)
        self.geometry("1200x650")
        self.resizable(True, True)

        # Données
        self.fichier_xml = insertions_xml
        self.gestionnaire = GestionnaireInsertion(self.fichier_xml)
        self._file_changed = False            # flag si l'utilisateur change les insertions
        self.data: dict[str, dict] = dict(self.gestionnaire.data)  # {spoken: {name, description, body}}

        # État
        self._dirty = False
        self._suspend_events = False
        self._current_iid: Optional[str] = None
        self._mode: str = "view"  # 'view' | 'edit' | 'new'

        # UI
        self._build_ui()
        self._load_table()
        self._set_mode("view", clear_form=True)

        # Fermeture
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------ UI ------------------
    def _build_ui(self) -> None:
        main = ttk.Frame(self)
        main.pack(fill="both", expand=True, padx=8, pady=8)

        # Zone centrale (tableau + formulaire)
        content = ttk.Frame(main)
        content.pack(side="top", fill="both", expand=True)

        # --- Tableau à gauche ---
        left = ttk.Frame(content)
        left.pack(side="left", fill="y")

        columns = ("name", "spoken", "description")
        self.tree = ttk.Treeview(left, columns=columns, show="headings", height=18)
        self.tree.heading("name", text="Nom")
        self.tree.heading("spoken", text="Forme prononcée")
        self.tree.heading("description", text="Description")
        self.tree.column("name", width=160, stretch=False)
        self.tree.column("spoken", width=180, stretch=False)
        self.tree.column("description", width=200, stretch=False)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.pack(side="left", fill="both", expand=True)

        yscroll = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        yscroll.pack(side="left", fill="y")
        self.tree.configure(yscrollcommand=yscroll.set)

        # --- Formulaire à droite ---
        form = ttk.Frame(content)
        form.pack(side="left", fill="both", expand=True, padx=(12, 0))

        ttk.Label(form, text="Nom *").grid(row=0, column=0, sticky="w")
        self.var_name = tk.StringVar()
        self.e_name = ttk.Entry(form, textvariable=self.var_name, width=36)
        self.e_name.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        ttk.Label(form, text="Description").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.var_desc = tk.StringVar()
        self.e_desc = ttk.Entry(form, textvariable=self.var_desc)
        self.e_desc.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(6, 0))

        ttk.Label(form, text="Forme prononcée *").grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.var_spoken = tk.StringVar()
        self.e_spoken = ttk.Entry(form, textvariable=self.var_spoken)
        self.e_spoken.grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=(6, 0))

        ttk.Label(form, text="Contenu *").grid(row=3, column=0, sticky="nw", pady=(6, 0))
        self.txt_body = tk.Text(form, height=12, wrap="word")
        self.txt_body.grid(row=3, column=1, sticky="nsew", padx=(8, 0), pady=(6, 0))
        self.txt_body.bind("<<Modified>>", self._on_text_modified)
        self.txt_body.edit_modified(False)

        form.grid_columnconfigure(1, weight=1)
        form.grid_rowconfigure(3, weight=1)

        # --- Séparateur + pied de page (tout en bas) ---
        ttk.Separator(main, orient="horizontal").pack(fill="x", pady=(6, 4))

        footer = ttk.Frame(main)
        footer.pack(side="bottom", fill="x")

        # À gauche : chemin du fichier
        self.lbl_file = ttk.Label(footer, text=f"Fichier : {self.fichier_xml}")
        self.lbl_file.pack(side="left")

        # À côté : actions fichier
        file_actions = ttk.Frame(footer)
        file_actions.pack(side="left", padx=12)
        ttk.Button(file_actions, text="Charger…", command=self._action_load_file).pack(side="left")
        ttk.Button(file_actions, text="Enregistrer sous…", command=self._action_save_as).pack(side="left", padx=6)

        # Espace extensible
        ttk.Frame(footer).pack(side="left", expand=True)

        # À droite : actions d'édition
        btns = ttk.Frame(footer)
        btns.pack(side="right")

        self.btn_add = ttk.Button(btns, text="Ajouter", command=self._add)
        self.btn_add.pack(side="left")

        self.btn_update = ttk.Button(btns, text="Mettre à jour",
                                     command=self._update, state=tk.DISABLED)
        self.btn_update.pack(side="left", padx=6)

        self.btn_delete = ttk.Button(btns, text="Supprimer", command=self._delete)
        self.btn_delete.pack(side="left")

        self.btn_save = ttk.Button(btns, text="Enregistrer",
                                   command=self._save, state=tk.DISABLED)
        self.btn_save.pack(side="left", padx=(12, 0))

        self.btn_close = ttk.Button(btns, text="Fermer", command=self._on_close)
        self.btn_close.pack(side="left", padx=(6, 0))

        # Détection des modifs (active _dirty)
        for v in (self.var_name, self.var_desc, self.var_spoken):
            v.trace_add("write", lambda *_: self._mark_dirty())

        # Initialiser l'état des boutons
        self._refresh_buttons()

    # ------------------ Data <-> UI ------------------
    def _load_table(self) -> None:
        self.tree.delete(*self.tree.get_children())
        items = sorted(self.data.items(), key=lambda kv: (kv[1]["name"] or "").lower())
        for idx, (spoken, e) in enumerate(items):
            iid = f"{idx}"
            self.tree.insert("", "end", iid=iid, values=(e.get("name", ""), spoken, e.get("description", "")))
        self._current_iid = None

    def _refresh_buttons(self) -> None:
        # En 'edit' ou 'new' → activer Enregistrer/Mettre à jour seulement si _dirty
        enable = (self._mode in ("edit", "new")) and self._dirty
        self.btn_update.configure(state=(tk.NORMAL if enable else tk.DISABLED))
        self.btn_save.configure(state=(tk.NORMAL if enable else tk.DISABLED))

    def _fill_form(self, *, name: str = "", desc: str = "", spoken: str = "", body: str = "") -> None:
        self._suspend_events = True
        try:
            self.var_name.set(name)
            self.var_desc.set(desc or "")
            self.var_spoken.set(spoken)
            prev_state = self.txt_body.cget("state")
            if prev_state == "disabled":
                self.txt_body.configure(state="normal")
            self.txt_body.delete("1.0", tk.END)
            self.txt_body.insert("1.0", body or "")
            self.txt_body.edit_modified(False)
            if prev_state == "disabled":
                self.txt_body.configure(state="disabled")
        finally:
            self._suspend_events = False

    # ------------------ État / Mode ------------------
    def _set_mode(self, mode: str, *, clear_form: bool = False) -> None:
        self._mode = mode
        if clear_form:
            self._fill_form()
        if mode == "view":
            self._disable_all()
        elif mode == "edit":
            # Nom verrouillé, le reste éditable
            self.e_name.configure(state="disabled")
            self.e_desc.configure(state="normal")
            self.e_spoken.configure(state="normal")
            self.txt_body.configure(state="normal")
        elif mode == "new":
            # Tout éditable
            self.e_name.configure(state="normal")
            self.e_desc.configure(state="normal")
            self.e_spoken.configure(state="normal")
            self.txt_body.configure(state="normal")
        self._refresh_buttons()

    def _disable_all(self) -> None:
        self.e_name.configure(state="disabled")
        self.e_desc.configure(state="disabled")
        self.e_spoken.configure(state="disabled")
        self.txt_body.configure(state="disabled")

    # ------------------ Helpers modifs ------------------
    def _on_text_modified(self, _evt=None) -> None:
        if self._suspend_events:
            self.txt_body.edit_modified(False)
            return
        if self.txt_body.edit_modified():
            self._mark_dirty()
        self.txt_body.edit_modified(False)

    def _mark_dirty(self) -> None:
        if self._suspend_events:
            return
        self._dirty = True
        self._refresh_buttons()
        try:
            self.title("Insertions *")
        except Exception:
            pass

    def _clear_dirty(self) -> None:
        self._dirty = False
        self._refresh_buttons()
        try:
            self.title("Insertions")
        except Exception:
            pass

    def _form_snapshot(self) -> dict:
        return {
            "name": (self.var_name.get() or "").strip(),
            "desc": (self.var_desc.get() or "").strip(),
            "spoken": (self.var_spoken.get() or "").strip(),
            "body": self.txt_body.get("1.0", tk.END).strip(),
        }

    def _has_unsaved_changes(self) -> bool:
        if self._dirty:
            return True
        snap = self._form_snapshot()
        if not any([snap["name"], snap["desc"], snap["spoken"], snap["body"]]):
            return False
        sel_spoken = self._selected_spoken()
        if self._mode == "edit" and sel_spoken and sel_spoken in self.data:
            orig = self.data[sel_spoken]
            return (
                snap["name"] != (orig.get("name", "") or "")
                or snap["desc"] != (orig.get("description", "") or "")
                or snap["body"] != (orig.get("body", "") or "")
                or snap["spoken"] != sel_spoken
            )
        # En mode 'new' avec des champs saisis -> changements non enregistrés
        return self._mode == "new"

    # ------------------ Sélection ------------------
    def _selected_spoken(self) -> Optional[str]:
        sel = self.tree.selection()
        if not sel:
            return None
        iid = sel[0]
        _name, spoken, _desc = self.tree.item(iid, "values")
        return spoken

    def _on_select(self, _evt=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]
        if self._dirty and self._current_iid is not None and iid != self._current_iid:
            if not messagebox.askyesno("Attention",
                                       "Modifications non enregistrées. Changer de sélection ?",
                                       parent=self):
                self.tree.selection_set(self._current_iid)
                return
        self._current_iid = iid
        _name, spoken, _desc = self.tree.item(iid, "values")
        e = self.data.get(spoken)
        if not e:
            return
        self._set_mode("edit")
        self._fill_form(name=e.get("name", ""), desc=e.get("description", ""), spoken=spoken, body=e.get("body", ""))
        self._clear_dirty()

    # ------------------ Actions ------------------
    def _add(self) -> None:
        if self._has_unsaved_changes():
            if not messagebox.askyesno("Attention", "Modifications non enregistrées. Continuer ?", parent=self):
                return
        self._current_iid = None
        self._set_mode("new", clear_form=True)
        self._clear_dirty()

    def _apply_snapshot_and_save(self, snap: dict, sel_spoken: Optional[str]) -> Optional[str]:
        """Applique le snapshot dans self.data (édition ou création) et sauvegarde. Retourne la spoken courante."""
        name, desc, spoken, body = snap["name"], snap["desc"], snap["spoken"], snap["body"]
        # Champs requis
        if not spoken or not body or (self._mode == "new" and not name):
            messagebox.showwarning("Champs obligatoires", "Nom, Forme prononcée et Contenu sont requis.", parent=self)
            return None

        if self._mode == "edit" and sel_spoken and sel_spoken in self.data:
            name_existing = self.data[sel_spoken].get("name", name)
            if spoken != sel_spoken:
                if spoken in self.data:
                    messagebox.showerror("Duplication",
                                         "Une insertion avec cette forme prononcée existe déjà.",
                                         parent=self)
                    return None
                del self.data[sel_spoken]
                self.data[spoken] = {"name": name_existing, "description": desc, "body": body}
            else:
                self.data[spoken] = {"name": name_existing, "description": desc, "body": body}
        else:
            if spoken in self.data:
                messagebox.showerror("Duplication",
                                     "Une insertion avec cette forme prononcée existe déjà.",
                                     parent=self)
                return None
            self.data[spoken] = {"name": name, "description": desc, "body": body}

        self._save_to_disk()
        return spoken

    def _update(self) -> None:
        snap = self._form_snapshot()
        spoken = self._apply_snapshot_and_save(snap, self._selected_spoken())
        if spoken is None:
            return
        self._load_table()
        self._select_by_spoken(spoken)
        self._set_mode("edit")
        self._clear_dirty()
        messagebox.showinfo("Insertions", "Enregistré", parent=self)

    def _delete(self) -> None:
        spoken = self._selected_spoken()
        if not spoken:
            messagebox.showwarning("Suppression", "Sélectionne une insertion.", parent=self)
            return
        if not messagebox.askyesno("Suppression", "Supprimer l'insertion sélectionnée ?", parent=self):
            return
        self.data.pop(spoken, None)
        self._save_to_disk()
        self._load_table()
        self._set_mode("view", clear_form=True)
        messagebox.showinfo("Insertions", "Insertion supprimée.", parent=self)

    def _save(self) -> None:
        snap = self._form_snapshot()
        spoken = self._apply_snapshot_and_save(snap, self._selected_spoken())
        if spoken is None:
            return
        self._load_table()
        self._select_by_spoken(spoken)
        self._set_mode("edit")
        self._clear_dirty()
        messagebox.showinfo("Insertions", "Enregistré", parent=self)

    # ------------------ Fichier externe ------------------
    def _update_file_label(self) -> None:
        try:
            self.lbl_file.configure(text=f"Fichier : {self.fichier_xml}")
        except Exception:
            pass

    def _switch_file(self, path: str) -> None:
        """Bascule l'éditeur sur un autre fichier d'insertions (lecture)."""
        try:
            new_mgr = GestionnaireInsertion(path)
            self.gestionnaire = new_mgr
            self.fichier_xml = self.gestionnaire.fichier_xml
            self._file_changed = True
            self.data = dict(self.gestionnaire.data)
            self._load_table()
            self._set_mode("view", clear_form=True)
            self._clear_dirty()
            self._update_file_label()
            self.title(self.fichier_xml)
        except Exception as e:
            messagebox.showerror("Ouverture", f"Impossible de charger le fichier:\n{e}", parent=self)

    def _action_load_file(self) -> None:
        # Proposer d'enregistrer les modifs en cours
        if self._has_unsaved_changes():
            res = messagebox.askyesnocancel("Enregistrer ?",
                                            "Enregistrer les modifications avant d'ouvrir un autre fichier ?",
                                            parent=self)
            if res is None:
                return
            if res:
                snap = self._form_snapshot()
                spoken = self._apply_snapshot_and_save(snap, self._selected_spoken())
                if spoken is None:
                    return
        path = filedialog.askopenfilename(parent=self, title="Ouvrir un fichier d'insertions",
                                          filetypes=[("XML", "*.xml"), ("Tous fichiers", "*.*")])
        if not path:
            return
        self._switch_file(path)

    def _action_save_as(self) -> None:
        path = filedialog.asksaveasfilename(parent=self, title="Enregistrer sous",
                                            defaultextension=".xml",
                                            filetypes=[("XML", "*.xml"), ("Tous fichiers", "*.*")])
        if not path:
            return
        # Met à jour la cible et sauvegarde
        self.fichier_xml = path
        self.gestionnaire.fichier_xml = path
        self.title(self.fichier_xml)
        try:
            self._save_to_disk()
            self._update_file_label()
            messagebox.showinfo("Enregistrer sous", "Fichier enregistré.", parent=self)
            self._file_changed = True
        except Exception as e:
            messagebox.showerror("Enregistrer sous", f"Erreur à l'enregistrement:\n{e}", parent=self)

    # ------------------ Persist ------------------
    def _save_to_disk(self) -> None:
        self.gestionnaire.data = dict(self.data)
        self.gestionnaire.sauvegarder_modifications()
        self._file_changed = True

    # ------------------ Utils ------------------
    def _select_by_spoken(self, spoken: str) -> None:
        for iid in self.tree.get_children():
            _name, sp, _d = self.tree.item(iid, "values")
            if sp == spoken:
                self.tree.selection_set(iid)
                self.tree.see(iid)
                self._current_iid = iid
                return

    # ------------------ Fermeture ------------------
    def _on_close(self) -> None:
        if self._has_unsaved_changes():
            res = messagebox.askyesnocancel("Fermer", "Enregistrer les modifications avant de fermer ?", parent=self)
            if res is None:
                return
            if res:
                snap = self._form_snapshot()
                spoken = self._apply_snapshot_and_save(snap, self._selected_spoken())
                if spoken is None:
                    return
        if self.fonction_termine:
            # On transmet le chemin effectivement utilisé (config ou perso)
            try:
                if self._file_changed:
                    self.master.after(0, self.fonction_termine(self.fichier_xml))
                else:
                    self.master.after(0, self.fonction_termine)
            except Exception:
                pass
        self.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Test - Éditeur d'insertions")
    win = FenetreInsertions(root, insertions_xml="insertions.xml")
    root.mainloop()
