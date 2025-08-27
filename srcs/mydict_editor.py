# mydict_editor.py
from __future__ import annotations
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import List, Dict, Any
from utils_window import get_config_path
import unicodedata
import os
import sys
import subprocess
import shutil
import struct


# --- phonemizer optionnel ---
try:
    from phonemizer import phonemize
    _HAS_PHONEMIZER = True
    _PHONEMIZER_IMPORT_ERR = ""
except Exception as e:
    import traceback
    _HAS_PHONEMIZER = False
    _PHONEMIZER_IMPORT_ERR = "".join(traceback.format_exception_only(type(e), e)).strip()

# MYDIC_PATH = get_config_path("my.dic")
# Emplacements standard espeak-ng (MSI Windows)
ESPEAK_DIR_DEFAULT = r"C:\Program Files\eSpeak NG"
ESPEAK_EXE_DEFAULT = os.path.join(ESPEAK_DIR_DEFAULT, "espeak-ng.exe")
ESPEAK_DLL_DEFAULT = os.path.join(ESPEAK_DIR_DEFAULT, "libespeak-ng.dll")


def ensure_espeak_env():
    r"""
    Renseigne les variables d'environnement utiles à phonemizer.
    Priorité :
      1) espeak-ng livré avec RecoVocale (dans {app}\espeak-ng)
      2) Installation système (Program Files\eSpeak NG)
    """
    base_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(__file__)
    local_dir = os.path.join(base_dir, "espeak-ng")
    local_exe = os.path.join(local_dir, "espeak-ng.exe")
    local_dll = os.path.join(local_dir, "libespeak-ng.dll")
    local_data = os.path.join(local_dir, "espeak-ng-data")

    if os.path.exists(local_exe) and os.path.exists(local_dll):
        # --- très important pour Windows 64-bit : aider le loader à trouver les dépendances ---
        try:
            os.add_dll_directory(local_dir)  # Python 3.8+
        except Exception as e:
            print(f"Erreur dans os.add_dll_directory({local_dir}) : {e}")
            pass

        os.environ.setdefault("PHONEMIZER_ESPEAK_PATH", local_dir)
        os.environ.setdefault("PHONEMIZER_ESPEAK_LIBRARY", local_dll)
        os.environ.setdefault("ESPEAK_PATH", local_exe)
        if os.path.isdir(local_data):
            os.environ.setdefault("ESPEAK_DATA_PATH", local_data)
        return

    # fallback MSI 64-bit
    system_dir = r"C:\Program Files\eSpeak NG"
    exe = os.path.join(system_dir, "espeak-ng.exe")
    dll = os.path.join(system_dir, "libespeak-ng.dll")
    data = os.path.join(system_dir, "espeak-ng-data")
    if os.path.exists(exe) and os.path.exists(dll):
        try:
            os.add_dll_directory(system_dir)
        except Exception:
            pass
        os.environ.setdefault("PHONEMIZER_ESPEAK_PATH", system_dir)
        os.environ.setdefault("PHONEMIZER_ESPEAK_LIBRARY", dll)
        os.environ.setdefault("ESPEAK_PATH", exe)
        if os.path.isdir(data):
            os.environ.setdefault("ESPEAK_DATA_PATH", data)


def _run(cmd: list[str]) -> tuple[int, str]:
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, shell=False)
        return 0, out.strip()
    except subprocess.CalledProcessError as e:
        return e.returncode, (e.output or "").strip()
    except Exception as e:
        return -1, str(e)


def phonemizer_is_ok(sample: str = "Sancare") -> tuple[bool, str]:
    """
    Teste l'appel phonemize() avec backend espeak.
    Retourne (ok, message).
    """
    if not _HAS_PHONEMIZER:
        return False, "Module phonemizer non installé (pip install phonemizer)."
    try:
        res = phonemize(sample, language="fr-fr", backend="espeak", strip=True)
        return True, f"OK: {res}"
    except Exception as e:
        return False, f"KO: {e}"


def build_phon_diag() -> str:
    """
    Construit un diagnostic texte détaillé : env, détections, versions, test.
    """

    lines = []
    lines.append(f"Process arch : {'64-bit' if struct.calcsize('P') == 8 else '32-bit'}")
    dllp = os.environ.get('PHONEMIZER_ESPEAK_LIBRARY') or ''
    lines.append(f"libespeak-ng.dll : {dllp} (exists={os.path.isfile(dllp)})")
    lines.append("=== Diagnostic phonémisation ===")
    lines.append(f"Python : {sys.version.split()[0]}  ({sys.executable})")
    lines.append(f"phonemizer installé : {_HAS_PHONEMIZER}")
    if not _HAS_PHONEMIZER and _PHONEMIZER_IMPORT_ERR:
        lines.append(f"phonemizer import error : {_PHONEMIZER_IMPORT_ERR}")
    lines.append("")
    # Variables d'env
    lines.append("[ENV]")
    lines.append(f"PHONEMIZER_ESPEAK_PATH   = {os.environ.get('PHONEMIZER_ESPEAK_PATH')}")
    lines.append(f"PHONEMIZER_ESPEAK_LIBRARY= {os.environ.get('PHONEMIZER_ESPEAK_LIBRARY')}")
    lines.append(f"ESPEAK_PATH              = {os.environ.get('ESPEAK_PATH')}")
    lines.append(f"PATH contains eSpeak NG? = {('eSpeak NG' in (os.environ.get('PATH') or ''))}")
    lines.append("")
    # which
    lines.append("[which]")
    lines.append(f"which('espeak')    = {shutil.which('espeak')}")
    lines.append(f"which('espeak-ng') = {shutil.which('espeak-ng')}")
    lines.append("")
    # versions CLI
    rc, out = _run(["espeak-ng", "--version"])
    lines.append("[espeak-ng --version]")
    lines.append(out or f"(rc={rc})")
    lines.append("")
    rc2, out2 = _run(["espeak", "--version"])
    lines.append("[espeak --version]")
    lines.append(out2 or f"(rc={rc2})")
    lines.append("")
    # test phonemizer
    ok, msg = phonemizer_is_ok("Sancare")
    lines.append("[phonemizer test]")
    lines.append(msg)
    lines.append("===============================")
    return "\n".join(lines)


def _load_dic(path: str) -> Dict[str, Any]:
    if not os.path.isabs(path) and not os.path.exists(path):
        path = get_config_path(path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("lang", "fr_FR")
        data.setdefault("entries", [])
        return data
    except FileNotFoundError:
        messagebox.showerror("my.dic", f"Fichier introuvable : {path}")
        return {"lang": "fr_FR", "entries": []}
    except Exception as e:
        messagebox.showerror("my.dic", f"Erreur lecture {path} : {e}")
        return {"lang": "fr_FR", "entries": []}


def _save_dic(data: Dict[str, Any], path: str) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        # --- NOTIF hot‑reload : invalider le cache du correcteur
        try:
            from mydict_corrector import invalidate_dict_cache
            invalidate_dict_cache()
        except Exception:
            pass
    except Exception as e:
        messagebox.showerror("my.dic", f"Erreur écriture {path} : {e}")


def _to_csv(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    return str(v)


def _from_csv(s: str) -> List[str]:
    if not s or not s.strip():
        return []
    return [x.strip() for x in s.split(",") if x.strip()]


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def _fallback_phonemize_fr(word: str) -> str:
    """
    Fallback ultra-léger si phonemizer n'est pas installé.
    NE PRÉTEND PAS être exact, juste 'pas vide'.
    """
    w = _strip_accents(word.lower())
    # très grossier : encode les nasales et quelques sons courants
    repl = (
        ("tion", "sjɔ̃"),
        ("sion", "zjɔ̃"),
        ("ain", "ɛ̃"),
        ("ein", "ɛ̃"),
        ("ien", "jɛ̃"),
        ("ienn", "jɛn"),
        ("an", "ɑ̃"),
        ("en", "ɑ̃"),
        ("on", "ɔ̃"),
        ("in", "ɛ̃"),
        ("un", "œ̃"),
        ("gn", "ɲ"),
        ("ch", "ʃ"),
        ("ph", "f"),
        ("th", "t"),
        ("qu", "k"),
        ("c", "k"),
    )
    for a, b in repl:
        w = w.replace(a, b)
    return w


def _phonemize_fr_list(items: List[str]) -> List[str]:
    items = [s.strip() for s in items if s and s.strip()]
    if not items:
        return []
    if _HAS_PHONEMIZER:
        try:
            ph = phonemize(items, language="fr-fr", strip=True, njobs=1, backend="espeak")
            # phonemize() peut renvoyer soit str soit list selon version
            if isinstance(ph, str):
                # quand input est list, certaines versions renvoient une string jointe par espaces/nouvelles lignes.
                # On re-split prudemment par '\n' d'abord, sinon par ' | ' si configuré différemment.
                parts = [p.strip() for p in ph.split("\n") if p.strip()]
            else:
                parts = [p.strip() for p in ph]
            return parts
        except Exception as e:
            print(f"Erreur dans _phonemize_fr_list({items}) : {e}")
            pass
    # fallback
    print("fallback")
    return [_fallback_phonemize_fr(x) for x in items]


class FenetreMyDict(tk.Toplevel):
    def __init__(self, master: tk.Misc, app=None, termine=None, path_dico: str = ""):
        super().__init__(master)
        self.modif = False
        self.app = app
        if os.path.isabs(path_dico) or os.path.exists(path_dico):
            self.path_dico = path_dico
        else:
            self.path_dico = get_config_path(self.app.config.dico)
        self.fonction_termine = termine
        self.title(f"Dictionnaire ({self.path_dico})")
        self.geometry("780x520")
        self._file_changed = False
        self.resizable(True, True)

        # Désactive le correcteur tant que la fenêtre est ouverte
        # et sauvegarde l'etat actuel
        if self.app and hasattr(self.app, "config"):
            self.ancien_etat_dictionnaire = self.app.config.dictionnaire
            self.app.config.dictionnaire = False
            self._set_status("Correction my.dic désactivée (édition du dictionnaire)")

        # --- Auto-setup espeak-ng pour la session (si présent à l'emplacement standard)
        ensure_espeak_env()

        # Données
        self.data = _load_dic(self.path_dico)
        self.entries: List[Dict[str, Any]] = self.data.get("entries", [])

        # Flag pour suspendre l'auto-phonémisation pendant les chargements programmatiques
        self._suspend_auto_phon = False

        # UI
        self._build_ui()
        self._load_table()

        # Fermeture propre
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        # === Barre de menus ===
        menubar = tk.Menu(self)
        # Fichier
        menu_fichier = tk.Menu(menubar, tearoff=False)
        menu_fichier.add_command(label="Charger…", command=self._action_load_file)
        menu_fichier.add_command(label="Enregistrer sous…", command=self._action_save_as)
        menubar.add_cascade(label="Fichier", menu=menu_fichier)
        # Diagnostique
        menu_diag = tk.Menu(menubar, tearoff=False)
        menu_diag.add_command(label="Diagnostic phonémisation…", command=self._open_phon_diag)
        menubar.add_cascade(label="Diagnostique", menu=menu_diag)
        self.config(menu=menubar)

        # === Tableau ===
        columns = ("word", "from", "phonemes", "weight", "tags")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=12)
        self.tree.heading("word", text="Mot")
        self.tree.heading("from", text="Approximations (liste)")
        self.tree.heading("phonemes", text="phonèmes (liste)")
        self.tree.heading("weight", text="Poids")
        self.tree.heading("tags", text="tags (liste)")
        self.tree.column("word", width=160)
        self.tree.column("from", width=210)
        self.tree.column("phonemes", width=170)
        self.tree.column("weight", width=70, anchor="center")
        self.tree.column("tags", width=120)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        # === Formulaire ===
        form = ttk.Frame(self)
        form.pack(fill="x", padx=8, pady=4)

        ttk.Label(form, text="Mot").grid(row=0, column=0, sticky="w")
        self.word_var = tk.StringVar()
        self.word_var.trace_add("write", lambda *_: (self._mark_modified(), self._refresh_buttons()))
        ttk.Entry(form, textvariable=self.word_var, width=30).grid(row=0, column=1, sticky="ew", padx=(6, 16))

        ttk.Label(form, text="Approximations (a,b,c)").grid(row=0, column=2, sticky="w")
        self.from_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.from_var, width=30).grid(row=0, column=3, sticky="ew", padx=(6, 16))

        # Auto-maj phonèmes lorsque 'from' change
        def _on_from_changed(*_):
            if getattr(self, "_suspend_auto_phon", False):
                return
            items = _from_csv(self.from_var.get())
            ph = _phonemize_fr_list(items)
            self.phonemes_var.set(", ".join(ph))
            self._mark_modified()
            self._refresh_buttons()
        self.from_var.trace_add("write", _on_from_changed)

        ttk.Label(form, text="phonèmes (a,b,c)").grid(row=1, column=0, sticky="w")
        self.phonemes_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.phonemes_var, width=30, state="readonly").grid(row=1, column=1, sticky="ew",
                                                                                         padx=(6, 16))

        ttk.Label(form, text="Poids").grid(row=1, column=2, sticky="w")
        self.weight_var = tk.StringVar(value="1.0")
        self.weight_var.trace_add("write", lambda *_: (self._mark_modified(), self._refresh_buttons()))
        ttk.Entry(form, textvariable=self.weight_var, width=10).grid(row=1, column=3, sticky="w", padx=(6, 16))

        ttk.Label(form, text="tags (a,b)").grid(row=2, column=0, sticky="w")
        self.tags_var = tk.StringVar()
        self.tags_var.trace_add("write", lambda *_: (self._mark_modified(), self._refresh_buttons()))
        ttk.Entry(form, textvariable=self.tags_var, width=30).grid(row=2, column=1, sticky="ew", padx=(6, 16))

        for i in range(4):
            form.grid_columnconfigure(i, weight=1)

        # === Boutons pied de page ===
        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=8, pady=(4, 8))

        # gauche
        self.btn_add = ttk.Button(btns, text="Ajouter", command=self._add)
        self.btn_add.pack(side="left")

        self.btn_duplicate = ttk.Button(btns, text="Dupliquer", command=self._duplicate, state=tk.DISABLED)
        self.btn_duplicate.pack(side="left", padx=6)

        self.btn_delete = ttk.Button(btns, text="Supprimer", command=self._delete, state=tk.DISABLED)
        self.btn_delete.pack(side="left", padx=6)

        self.btn_update = ttk.Button(btns, text="Mettre à jour", command=self._update, state=tk.DISABLED)
        self.btn_update.pack(side="left", padx=6)

        # droite
        self.btn_save = ttk.Button(btns, text="Enregistrer", command=self._save, state=tk.DISABLED)
        self.btn_save.pack(side="right")

        self.btn_close = ttk.Button(btns, text="Fermer", command=self._on_close)
        self.btn_close.pack(side="right", padx=(6, 0))

        # Etiquette chemin
        ttk.Label(self, text=f"Fichier : {self.path_dico}").pack(anchor="w", padx=8, pady=(0, 8))

        # Init états
        self._refresh_buttons()

    def _refresh_buttons(self) -> None:
        has_sel = bool(self.tree.selection())
        # Update/Save : seulement si de vraies modifs (self.modif)
        self.btn_save.configure(state=(tk.NORMAL if self.modif else tk.DISABLED))
        # Mettre à jour a besoin d'une sélection + modifs
        self.btn_update.configure(state=(tk.NORMAL if (self.modif and has_sel) else tk.DISABLED))
        # Supprimer & Dupliquer : accessibles uniquement si une ligne est sélectionnée
        self.btn_delete.configure(state=(tk.NORMAL if has_sel else tk.DISABLED))
        self.btn_duplicate.configure(state=(tk.NORMAL if has_sel else tk.DISABLED))

    def _update_file_label(self) -> None:
        """Met à jour l’étiquette du chemin courant + le titre de la fenêtre."""
        try:
            self.lbl_file.configure(text=f"Fichier : {self.path_dico}")
            self.title(f"Dictionnaire ({self.path_dico})")
        except Exception:
            pass

    def _switch_file(self, path: str) -> None:
        """
        Bascule l’éditeur sur un autre fichier my.dic (lecture).
        Conserve self.entries et recharge la table. Marque _file_changed.
        """
        try:
            # Recharge
            self.path_dico = path if (os.path.isabs(path) or os.path.exists(path)) else get_config_path(path)
            self.data = _load_dic(self.path_dico)
            self.entries = self.data.get("entries", [])
            self._file_changed = True

            # UI
            self._load_table()
            # reset du formulaire
            self._suspend_auto_phon = True
            try:
                self.word_var.set("")
                self.from_var.set("")
                self.phonemes_var.set("")
                self.weight_var.set("1.0")
                self.tags_var.set("")
            finally:
                self._suspend_auto_phon = False

            # statut/visuel
            self._update_file_label()
            self.modif = False
        except Exception as e:
            messagebox.showerror("Ouverture", f"Impossible de charger le fichier :\n{e}", parent=self)

    def _action_load_file(self) -> None:
        """Menu Fichier > Charger…  (propose d’enregistrer si modif)"""
        if self.modif:
            res = messagebox.askyesnocancel("Enregistrer ?",
                                            "Enregistrer les modifications avant d'ouvrir un autre fichier ?",
                                            parent=self)
            if res is None:
                return
            if res:
                self._save()

        path = filedialog.askopenfilename(parent=self,
                                          title="Ouvrir un dictionnaire",
                                          filetypes=[("Dictionnaire JSON", "*.dic;*.json"),
                                                     ("Tous fichiers", "*.*")])
        if not path:
            return
        self._switch_file(path)

    def _action_save_as(self) -> None:
        """Menu Fichier > Enregistrer sous…  (change la cible puis sauvegarde)"""
        path = filedialog.asksaveasfilename(parent=self,
                                            title="Enregistrer le dictionnaire sous",
                                            defaultextension=".dic",
                                            filetypes=[("Dictionnaire JSON", "*.dic"),
                                                       ("JSON", "*.json"),
                                                       ("Tous fichiers", "*.*")])
        if not path:
            return
        self.path_dico = path
        self._update_file_label()
        # Sauvegarde via la méthode existante (gère invalidation cache)
        self._save()
        self._file_changed = True

    def _open_phon_diag(self):
        """Affiche une fenêtre modale avec le diagnostic détaille et un bouton 'Copier'."""
        txt = build_phon_diag()

        win = tk.Toplevel(self)
        win.title("Diagnostic phonémisation")
        win.geometry("800x500")
        win.transient(self)
        win.grab_set()

        frm = ttk.Frame(win)
        frm.pack(fill="both", expand=True, padx=8, pady=8)

        textw = tk.Text(frm, wrap="word")
        textw.insert("1.0", txt)
        textw.configure(state="disabled")
        textw.pack(fill="both", expand=True)

        btns = ttk.Frame(win)
        btns.pack(fill="x", padx=8, pady=(6, 0))

        def _copy():
            try:
                self.clipboard_clear()
                self.clipboard_append(txt)
                messagebox.showinfo("Diagnostic", "Copié dans le presse-papiers ✅")
            except Exception as e:
                messagebox.showerror("Diagnostic", f"Impossible de copier : {e}")
        ttk.Button(btns, text="Copier", command=_copy).pack(side="left")
        ttk.Button(btns, text="Fermer", command=win.destroy).pack(side="right")

    def _set_status(self, msg: str):
        try:
            mode = getattr(self.app, "current_mode", None)
            if mode and hasattr(mode, "status_bar"):
                from utils_window import update_status_bar
                update_status_bar(mode.status_bar, text=msg, bg="lightblue", fg="darkblue", anchor="w")
        except Exception:
            pass

    def _load_table(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for idx, e in enumerate(self.entries):
            self.tree.insert(
                "", "end", iid=str(idx),
                values=(
                    e.get("word", ""),
                    _to_csv(e.get("from") or e.get("aliases") or []),
                    _to_csv(e.get("phonemes", [])),
                    e.get("weight", 1.0),
                    _to_csv(e.get("tags", [])),
                )
            )
        self._refresh_buttons()

    def _on_select(self, _evt=None):
        sel = self.tree.selection()
        if not sel:
            return
        i = int(sel[0])
        e = self.entries[i]
        self._suspend_auto_phon = True
        try:
            self.word_var.set(e.get("word", ""))
            self.from_var.set(_to_csv(e.get("from") or e.get("aliases") or []))
            self.phonemes_var.set(_to_csv(e.get("phonemes", [])))
            self.weight_var.set(str(e.get("weight", 1.0)))
            self.tags_var.set(_to_csv(e.get("tags", [])))
        finally:
            self._suspend_auto_phon = False
            self._refresh_buttons()

    def _current_entry_from_form(self) -> Dict[str, Any]:
        word = self.word_var.get().strip()
        if not word:
            raise ValueError("Le champ 'word' est obligatoire.")
        try:
            weight = float(self.weight_var.get().strip() or "1.0")
        except ValueError:
            raise ValueError("Le champ 'weight' doit être un nombre.")
        from_list = _from_csv(self.from_var.get())
        ph_list = _from_csv(self.phonemes_var.get())

        # Si tailles différentes ou phonèmes vides -> recalcule pour aligner
        if len(ph_list) != len(from_list) or (not ph_list and from_list):
            ph_list = _phonemize_fr_list(from_list)
            # reflète à l'écran pour transparence
            self.phonemes_var.set(", ".join(ph_list))

        return {
            "word": word,
            "from": from_list,
            "phonemes": ph_list,
            "weight": weight,
            "tags": _from_csv(self.tags_var.get()),
        }

    def _add(self):
        try:
            e = self._current_entry_from_form()
        except Exception as e:
            messagebox.showerror("Ajout", str(e))
            return
        self.entries.append(e)
        self._load_table()
        self._select_last()
        self._mark_modified()

    def _update(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Modification", "Sélectionne une entrée.")
            return
        i = int(sel[0])
        try:
            e = self._current_entry_from_form()
        except Exception as ex:
            messagebox.showerror("Modification", str(ex))
            return
        self.entries[i] = e
        self._load_table()
        self.tree.selection_set(str(i))
        self._mark_modified()

    def _mark_modified(self):
        if getattr(self, "_suspend_auto_phon", False):
            return
        self.modif = True
        try:
            self.title(f"Dictionnaire ({self.path_dico}) *")  # petit indicateur visuel
        except Exception:
            pass
        self._refresh_buttons()

    def _delete(self):
        sel = self.tree.selection()
        if not sel:
            return
        i = int(sel[0])
        if messagebox.askyesno("Suppression", "Supprimer l'entrée sélectionnée ?"):
            del self.entries[i]
            self._load_table()
            self.word_var.set("")
            self.from_var.set("")
            self.phonemes_var.set("")
            self.weight_var.set("1.0")
            self.tags_var.set("")
            self._mark_modified()

    def _duplicate(self):
        sel = self.tree.selection()
        if not sel:
            return
        i = int(sel[0])
        e = dict(self.entries[i])
        e["word"] = e.get("word", "") + "_copy"
        self.entries.append(e)
        self._load_table()
        self._select_last()
        self._mark_modified()

    def _select_last(self):
        if not self.entries:
            return
        last = len(self.entries) - 1
        self.tree.selection_set(str(last))
        self.tree.see(str(last))

    def _save(self):
        self.data["entries"] = self.entries
        _save_dic(self.data, self.path_dico)
        messagebox.showinfo(f"{self.path_dico}", "Enregistré")
        self.modif = False
        try:
            self.title(f"Dictionnaire ({self.path_dico})")
        except Exception:
            pass

    def _on_close(self):
        if self.modif:
            if messagebox.askyesno("Fermer", "Enregistrer les modifications avant de fermer ?"):
                self._save()
        if self.app and hasattr(self.app, "config"):
            self.app.config.dictionnaire = self.ancien_etat_dictionnaire
            self._set_status("Correction my.dic réactivée" if self.app.config.dictionnaire
                             else "Correction my.dic désactivée")
        if self.fonction_termine:
            try:
                if self._file_changed:
                    self.master.after(0, self.fonction_termine(self.path_dico))
                else:
                    self.master.after(0, self.fonction_termine)
            except Exception:
                pass

        self.destroy()
