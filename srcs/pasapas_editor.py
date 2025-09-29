from __future__ import annotations
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Any, Dict, List, Optional
from pas_a_pas import Executor
from utils_window import get_config_path, update_status_bar


# --- Info-bulles (no border, black on yellow) ---
class _BubbleTip:
    def __init__(self, widget, text: str, delay=350):
        self.widget = widget
        self.text = text
        self.delay = delay
        self._tw = None
        self._after = None
        widget.bind("<Enter>", self._schedule)
        widget.bind("<Leave>", self._hide)
        widget.bind("<ButtonPress>", self._hide)

    def _schedule(self, e):
        self._cancel()
        self._after = self.widget.after(self.delay, lambda: self._show(e))

    def _cancel(self):
        if self._after:
            try:
                self.widget.after_cancel(self._after)
            except Exception:
                pass
            self._after = None

    def _show(self, e):
        if self._tw:
            return
        x, y = e.x_root + 12, e.y_root + 8
        tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.attributes("-topmost", True)
        # fond jaune, texte noir, pas de bordure
        frm = tk.Frame(tw, bg="#f8e36e", bd=0, highlightthickness=0)
        frm.pack()
        lab = tk.Label(frm, text=self.text, justify=tk.LEFT,
                       bg="#f8e36e", fg="#000000", padx=8, pady=4,
                       bd=0, highlightthickness=0)
        lab.pack()
        tw.geometry(f"+{x}+{y}")
        self._tw = tw

    def _hide(self, _=None):
        self._cancel()
        if self._tw:
            try:
                self._tw.destroy()
            except Exception:
                pass
            self._tw = None


def add_tip(widget, text: str):
    _BubbleTip(widget, text)


# Types d'étapes pris en charge (alignés avec pas_a_pas.StepType)
STEP_TYPES = [
    "open_app",         # target, args, window
    "wait",             # ms
    "send_keys",        # keys (list)
    "wait_window",      # title_contains/title_regex/class_name/pid/timeout_ms/require_visible/activate
    "execute_command",  # name (référence autre commande)
]

WINDOW_MODES = ["normal", "minimized", "maximized"]


# ----------------- Helpers JSON -----------------
def _load_pp(path: str) -> List[Dict[str, Any]]:
    """
    Charge un fichier pas_a_pas.json et retourne une liste de commandes.
    Garantit la présence des clés minimales.
    """
    if not os.path.isabs(path) and not os.path.exists(path):
        path = get_config_path(path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("Le fichier pas à pas doit contenir une liste de commandes.")
        # normalisation légère
        out = []
        for obj in data:
            out.append({
                "name": obj.get("name", ""),
                "spoken": obj.get("spoken", ""),
                "description": obj.get("description", ""),
                "steps": list(obj.get("steps", [])),
            })
        return out
    except FileNotFoundError:
        messagebox.showerror("Pas à pas", f"Fichier introuvable : {path}")
        return []
    except Exception as e:
        messagebox.showerror("Pas à pas", f"Erreur lecture {path} : {e}")
        return []


def _save_pp(commands: List[Dict[str, Any]], path: str) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(commands, f, ensure_ascii=False, indent=2)
        messagebox.showinfo(os.path.basename(path) or "pas_a_pas.json", "Enregistré")
    except Exception as e:
        messagebox.showerror("Pas à pas", f"Erreur écriture {path} : {e}")


# ----------------- Helpers UI -----------------
def _params_to_preview(p: Dict[str, Any]) -> str:
    if not p:
        return ""
    # on compacte quelques cas fréquents pour un aperçu lisible
    if "target" in p:
        tgt = p.get("target", "")
        args = p.get("args", "")
        verb = p.get("verb", "open")
        return f"target={os.path.basename(tgt) or tgt} args={args!r} verb={verb}"
    if "ms" in p:
        return f"{p.get('ms')} ms"
    if "keys" in p:
        # n'affiche pas tout si long
        k = p.get("keys", [])
        if isinstance(k, list):
            joined = ", ".join(map(str, k))
        else:
            joined = str(k)
        return (joined[:60] + "…") if len(joined) > 60 else joined
    if "title_contains" in p or "title_regex" in p:
        tc = p.get("title_contains")
        tr = p.get("title_regex")
        return f"title_contains={tc!r} title_regex={tr!r}"
    if "name" in p:
        return f"name={p.get('name')}"

    # fallback générique
    try:
        s = json.dumps(p, ensure_ascii=False)
        return (s[:60] + "…") if len(s) > 60 else s
    except Exception:
        return str(p)


def _split_csv(s: str) -> List[str]:
    if not s or not s.strip():
        return []
    return [x.strip() for x in s.split(",") if x.strip()]


# ----------------- Fenêtre d'édition de step -----------------
class StepEditor(tk.Toplevel):
    """Dialogue modal pour ajouter/modifier une étape.
    Retour via self.result = {"type": str, "params": dict} ou None si annulé.
    """

    def __init__(self, master: tk.Misc, step: Optional[Dict[str, Any]] = None,
                 command_names: Optional[List[str]] = None):
        super().__init__(master)
        self.title("Édition d'une étape")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self._command_names = command_names or []
        s = step or {"type": "wait", "params": {"ms": 500}}
        self.var_type = tk.StringVar(value=s.get("type", "wait"))
        self.widgets_frame = None
        self._field_vars: Dict[str, tk.Variable] = {}
        self.result: Optional[Dict[str, Any]] = None

        frm = ttk.Frame(self)
        frm.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(frm, text="Type d'étape").grid(row=0, column=0, sticky="w")
        cb = ttk.Combobox(frm, values=STEP_TYPES, textvariable=self.var_type, state="readonly", width=20)
        cb.grid(row=0, column=1, sticky="w")
        cb.bind("<<ComboboxSelected>>", lambda e: self._rebuild_fields(frm))

        # zone dynamique pour les champs
        self.widgets_frame = ttk.Frame(frm)
        self.widgets_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(8, 0))
        frm.grid_columnconfigure(1, weight=1)

        # boutons
        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=10, pady=(8, 10))
        ttk.Button(btns, text="Annuler", command=self._cancel).pack(side="right")
        ttk.Button(btns, text="OK", command=self._ok).pack(side="right", padx=(0, 6))

        # initial
        self._rebuild_fields(frm, initial_params=s.get("params", {}))

    def _rebuild_fields(self, container: ttk.Frame, initial_params: Optional[Dict[str, Any]] = None):
        # reset
        for w in list(self.widgets_frame.children.values()):
            w.destroy()
        self._field_vars.clear()
        t = self.var_type.get()
        p = initial_params or {}

        def add_row(label: str, var: tk.Variable, row: int, widget: Optional[tk.Widget] = None):
            ttk.Label(self.widgets_frame, text=label).grid(row=row, column=0, sticky="w")
            if widget is None:
                ent = ttk.Entry(self.widgets_frame, textvariable=var, width=40)
            else:
                ent = widget
            ent.grid(row=row, column=1, sticky="ew", padx=(8, 0))
            self.widgets_frame.grid_columnconfigure(1, weight=1)
            return ent

        row = 0
        if t == "open_app":
            v_tgt = tk.StringVar(value=p.get("target", ""))
            v_args = tk.StringVar(value=p.get("args", ""))
            v_win = tk.StringVar(value=p.get("window", "normal"))
            v_verb = tk.StringVar(value=p.get("verb", "open"))
            self._field_vars.update(target=v_tgt, args=v_args, window=v_win, verb=v_verb)
            # champ cible + bouton parcourir
            ent = add_row("Cible", v_tgt, row)
            row += 1
            add_tip(ent, "Chemin complet de l’exécutable à lancer (ex: C:\\Program Files\\...\\app.exe).")

            def browse():
                path = filedialog.askopenfilename(parent=self, title="Choisir l'exécutable")
                if path:
                    v_tgt.set(path)
            b = ttk.Button(self.widgets_frame, text="Parcourir…", command=browse)
            b.grid(row=row-1, column=2, padx=6)
            ent = add_row("Arguments", v_args, row)
            row += 1
            add_tip(ent, "Arguments de ligne de commande (URL, options…). "
                    "Si l’argument contient des espaces, garde les guillemets.")
            cb = ttk.Combobox(self.widgets_frame, values=WINDOW_MODES, textvariable=v_win, state="readonly", width=12)
            ent = add_row("Fenêtre", v_win, row, widget=cb)
            row += 1
            add_tip(ent, "Mode d’affichage de la fenêtre : normal, minimized, maximized.")
            cb_verb = ttk.Combobox(self.widgets_frame, values=["open", "print", "edit"],
                                   textvariable=v_verb, state="readonly", width=12)
            ent = add_row("Action (verb)", v_verb, row, widget=cb_verb)
            add_tip(ent, "Action ShellExecute : 'open' = ouvrir avec l’application par défaut, "
                         "'print' = imprimer via l’appli par défaut, 'edit' = ouvrir en édition (si supporté). "
                         "Utile pour les fichiers non exécutables (PDF, DOCX, URL…).")
            row += 1

        elif t == "wait":
            v_ms = tk.StringVar(value=str(p.get("ms", 500)))
            self._field_vars.update(ms=v_ms)
            ent = add_row("Durée (ms)", v_ms, row)
            add_tip(ent, "Temps d’attente en millisecondes (1000 = 1 seconde).")
            row += 1

        elif t == "send_keys":
            # saisie sous forme "{TAB}, Hello, {ENTER}"
            keys = p.get("keys", [])
            if isinstance(keys, list):
                s = ", ".join(map(str, keys))
            else:
                s = str(keys)
            v_keys = tk.StringVar(value=s)
            self._field_vars.update(keys=v_keys)
            ent = add_row("Touches (séparées par ,)", v_keys, row)
            row += 1
            add_tip(ent, (
                "Sépare par des virgules. Exemples : {TAB}, Bonjour, {ENTER}  •  {CTRL}, v\n"
                "Touches supportées : {ENTER}, {TAB}, {ESC}, {DEL}/{DELETE}, {BACKSPACE}, "
                "{UP}, {DOWN}, {LEFT}, {RIGHT}, {CTRL}, {ALT}, {SHIFT}, {SPACE}.\n"
                "Texte libre accepté. Combinaisons: {CTRL}, v. "
                "\"{TAB}{ENTER}\" dans une même chaîne fonctionne aussi."
            ))
            ttk.Label(self.widgets_frame, text="Exemples: {TAB}, Bonjour, {ENTER}  •  {CTRL}, v").grid(row=row,
                                                                                                       column=1,
                                                                                                       sticky="w",
                                                                                                       pady=(4, 0))
            row += 1

        elif t == "wait_window":
            v_tc = tk.StringVar(value=p.get("title_contains", ""))
            v_tr = tk.StringVar(value=p.get("title_regex", ""))
            v_cls = tk.StringVar(value=p.get("class_name", ""))
            v_pid = tk.StringVar(value=str(p.get("pid", "")))
            v_to = tk.StringVar(value=str(p.get("timeout_ms", 10000)))
            v_vis = tk.BooleanVar(value=bool(p.get("require_visible", True)))
            v_act = tk.BooleanVar(value=bool(p.get("activate", True)))
            v_max = tk.BooleanVar(value=bool(p.get("maximize", False)))
            self._field_vars.update(title_contains=v_tc, title_regex=v_tr, class_name=v_cls,
                                    pid=v_pid, timeout_ms=v_to, require_visible=v_vis, activate=v_act, maximize=v_max)
            ent = add_row("Titre contient", v_tc, row)
            row += 1
            add_tip(ent, "Sous-chaîne attendue dans le titre de la fenêtre (insensible à la casse).")
            ent = add_row("Titre (regex)", v_tr, row)
            row += 1
            add_tip(ent, "Expression régulière appliquée au titre (avancé).")
            ent = add_row("Classe fenêtre", v_cls, row)
            row += 1
            add_tip(ent, "Nom de classe Win32 (avancé)")
            ent = add_row("PID (optionnel)", v_pid, row)
            row += 1
            add_tip(ent, "Filtre par PID du processus si nécessaire (avancé).")
            ent = add_row("Timeout (ms)", v_to, row)
            row += 1
            add_tip(ent, "Délai maximum d’attente avant d’abandonner (ms).")
            chk1 = ttk.Checkbutton(self.widgets_frame, text="Fenêtre visible requise", variable=v_vis)
            add_tip(chk1, "Si coché : ignore les fenêtres non visibles (masquées/minimisées).")
            chk1.grid(row=row, column=1, sticky="w", pady=(4, 0))
            row += 1
            chk2 = ttk.Checkbutton(self.widgets_frame, text="Activer la fenêtre si trouvée", variable=v_act)
            add_tip(chk2, "Met la fenêtre trouvée au premier plan (SetForegroundWindow).")
            chk2.grid(row=row, column=1, sticky="w")
            row += 1
            chk3 = ttk.Checkbutton(self.widgets_frame, text="Maximiser la fenêtre si trouvée", variable=v_max)
            chk3.grid(row=row, column=1, sticky="w")
            row += 1

        elif t == "execute_command":
            v_name = tk.StringVar(value=p.get("name", ""))
            self._field_vars.update(name=v_name)
            # si on a la liste des commandes existantes => combobox
            if self._command_names:
                cb = ttk.Combobox(self.widgets_frame, values=self._command_names, textvariable=v_name, width=40)
                add_row("Nom commande", v_name, row, widget=cb)
                row += 1
            else:
                add_row("Nom commande", v_name, row)
                row += 1

        else:
            ttk.Label(self.widgets_frame, text=f"Type inconnu: {t}").grid(row=row, column=0, sticky="w")

    def _ok(self):
        t = self.var_type.get()
        p: Dict[str, Any] = {}
        for k, var in self._field_vars.items():
            val: Any = var.get()
            if isinstance(var, tk.BooleanVar):
                p[k] = bool(val)
            else:
                txt = str(val).strip()
                if txt == "":
                    # on omet les champs vides pour alléger
                    continue
                if t == "wait" and k == "ms":
                    try:
                        p[k] = int(txt)
                    except Exception:
                        messagebox.showerror("Étape", "La durée (ms) doit être un entier.", parent=self)
                        return
                elif t == "wait_window" and k in {"pid", "timeout_ms"}:
                    try:
                        p[k] = int(txt)
                    except Exception:
                        messagebox.showerror("Étape", f"{k} doit être un entier.", parent=self)
                        return
                elif t == "send_keys" and k == "keys":
                    p[k] = _split_csv(txt)
                else:
                    p[k] = txt
        self.result = {"type": t, "params": p}
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


# ----------------- Fenêtre principale -----------------
class FenetrePasAPas(tk.Toplevel):
    def __init__(self, master: tk.Misc, app=None, termine=None, path_json: str = ""):
        super().__init__(master)
        self.app = app
        self.termine_cb = termine
        self.path_json = path_json or (getattr(getattr(app, "config", object), "pas_a_pas", "pas_a_pas.json"))
        if not os.path.isabs(self.path_json) and not os.path.exists(self.path_json):
            self.path_json = get_config_path(self.path_json)

        self.title(f"Commandes Pas à pas ({self.path_json})")
        self.geometry("980x800")
        self.resizable(True, True)

        self.commands: List[Dict[str, Any]] = _load_pp(self.path_json)
        self.modif = False
        self._build_ui()
        self._load_commands()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---- UI ----
    def _build_ui(self):
        # menu
        menubar = tk.Menu(self)
        m_file = tk.Menu(menubar, tearoff=False)
        m_file.add_command(label="Charger…", command=self._action_load)
        m_file.add_command(label="Enregistrer sous…", command=self._action_save_as)
        menubar.add_cascade(label="Fichier", menu=m_file)
        self.config(menu=menubar)

        # split horizontal: commandes (haut) / détails + steps (bas)
        top = ttk.Frame(self)
        top.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        # --- tableau des commandes ---
        columns = ("name", "spoken", "description")
        self.tree_cmd = ttk.Treeview(top, columns=columns, show="headings", height=9)
        self.tree_cmd.heading("name", text="Nom")
        self.tree_cmd.heading("spoken", text="Forme prononcée")
        self.tree_cmd.heading("description", text="Description")
        self.tree_cmd.column("name", width=200)
        self.tree_cmd.column("spoken", width=220)
        self.tree_cmd.column("description", width=420)
        self.tree_cmd.bind("<<TreeviewSelect>>", self._on_cmd_select)
        self.tree_cmd.pack(fill="both", expand=True)

        # barre boutons commandes
        cmd_btns = ttk.Frame(self)
        cmd_btns.pack(fill="x", padx=8, pady=(2, 8))
        self.btn_cmd_add = ttk.Button(cmd_btns, text="Ajouter", command=self._cmd_add)
        self.btn_cmd_dup = ttk.Button(cmd_btns, text="Dupliquer", command=self._cmd_duplicate, state=tk.DISABLED)
        self.btn_cmd_del = ttk.Button(cmd_btns, text="Supprimer", command=self._cmd_delete, state=tk.DISABLED)
        self.btn_cmd_upd = ttk.Button(cmd_btns, text="Mettre à jour", command=self._cmd_update, state=tk.DISABLED)
        for b in (self.btn_cmd_add, self.btn_cmd_dup, self.btn_cmd_del, self.btn_cmd_upd):
            b.pack(side="left", padx=(0, 6))

        # --- formulaire commande ---
        form = ttk.LabelFrame(self, text="Commande")
        form.pack(fill="x", padx=8, pady=(0, 8))

        ttk.Label(form, text="Nom").grid(row=0, column=0, sticky="w")
        self.var_name = tk.StringVar()
        ttk.Entry(form, textvariable=self.var_name, width=30).grid(row=0, column=1, sticky="ew", padx=(6, 16))

        ttk.Label(form, text="Forme prononcée").grid(row=0, column=2, sticky="w")
        self.var_spoken = tk.StringVar()
        ttk.Entry(form, textvariable=self.var_spoken, width=30).grid(row=0, column=3, sticky="ew", padx=(6, 16))

        ttk.Label(form, text="Description").grid(row=1, column=0, sticky="w")
        self.var_desc = tk.StringVar()
        ttk.Entry(form, textvariable=self.var_desc).grid(row=1, column=1, columnspan=3, sticky="ew", padx=(6, 16))

        # activer Enregistrer dès qu'on tape dans le formulaire
        for _v in (self.var_name, self.var_spoken, self.var_desc):
            _v.trace_add("write", lambda *_: self._mark_modified())

        for i in range(4):
            form.grid_columnconfigure(i, weight=1)

        # --- steps ---
        steps = ttk.LabelFrame(self, text="Étapes")
        steps.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        scroller = ttk.Frame(steps)
        scroller.pack(fill="both", expand=True)

        self.tree_steps = ttk.Treeview(scroller, columns=("idx", "type", "params"), show="headings", height=10)
        self.tree_steps.heading("idx", text="#")
        self.tree_steps.heading("type", text="Type")
        self.tree_steps.heading("params", text="Paramètres (aperçu)")
        self.tree_steps.column("idx", width=40, anchor="center")
        self.tree_steps.column("type", width=180)
        self.tree_steps.column("params", width=600)
        self.tree_steps.bind("<<TreeviewSelect>>", lambda _e: self._refresh_buttons())
        self.tree_steps.bind("<Double-1>", self._on_step_double_click)
        self.tree_steps.bind("<Return>", lambda _e: self._step_edit())
        self.tree_steps.pack(fill="both", expand=True)

        btns = ttk.Frame(steps)
        btns.pack(fill="x", pady=(6, 0))
        self.btn_step_add = ttk.Button(btns, text="Ajouter", command=self._step_add)
        self.btn_step_edit = ttk.Button(btns, text="Modifier", command=self._step_edit, state=tk.DISABLED)
        self.btn_step_del = ttk.Button(btns, text="Supprimer", command=self._step_delete, state=tk.DISABLED)
        self.btn_step_up = ttk.Button(btns, text="Monter", command=lambda: self._step_move(-1), state=tk.DISABLED)
        self.btn_step_down = ttk.Button(btns, text="Descendre", command=lambda: self._step_move(1), state=tk.DISABLED)
        for b in (self.btn_step_add, self.btn_step_edit, self.btn_step_del, self.btn_step_up, self.btn_step_down):
            b.pack(side="left", padx=(0, 6))

        # --- pied ---
        footer = ttk.Frame(self)
        footer.pack(fill="x", padx=8, pady=(0, 8))
        self.btn_save = ttk.Button(footer, text="Enregistrer", command=self._save, state=tk.DISABLED)
        self.btn_close = ttk.Button(footer, text="Fermer", command=self._on_close)
        self.lbl_file = ttk.Label(footer, text=f"Fichier : {self.path_json}")
        self.btn_save.pack(side="right")
        self.btn_close.pack(side="right", padx=(6, 0))
        self.lbl_file.pack(side="left")

        self._refresh_buttons()

    # ---- Chargement & rafraîchissement ----
    def _load_commands(self):
        self.tree_cmd.delete(*self.tree_cmd.get_children())
        for i, cmd in enumerate(self.commands):
            self.tree_cmd.insert("", "end", iid=str(i), values=(cmd.get("name", ""),
                                                                cmd.get("spoken", ""),
                                                                cmd.get("description", "")))
        self._refresh_buttons()

    def _load_steps(self, steps_list: List[Dict[str, Any]]):
        self.tree_steps.delete(*self.tree_steps.get_children())
        for i, st in enumerate(steps_list):
            self.tree_steps.insert("", "end", iid=str(i), values=(i+1, st.get("type", ""),
                                                                  _params_to_preview(st.get("params", {}))))
        self._refresh_buttons()

    def _get_selected_cmd_idx(self) -> Optional[int]:
        sel = self.tree_cmd.selection()
        if not sel:
            return None
        try:
            return int(sel[0])
        except Exception:
            return None

    def _get_selected_step_idx(self) -> Optional[int]:
        sel = self.tree_steps.selection()
        if not sel:
            return None
        try:
            return int(sel[0])
        except Exception:
            return None

    # ---- Boutons état ----
    def _refresh_buttons(self):
        has_cmd = bool(self.tree_cmd.selection())
        has_step = bool(self.tree_steps.selection())
        self.btn_cmd_dup.configure(state=tk.NORMAL if has_cmd else tk.DISABLED)
        self.btn_cmd_del.configure(state=tk.NORMAL if has_cmd else tk.DISABLED)
        # update actif si champ modifié et une commande est sélectionnée
        self.btn_cmd_upd.configure(state=tk.NORMAL if has_cmd else tk.DISABLED)

        self.btn_step_edit.configure(state=tk.NORMAL if has_step else tk.DISABLED)
        self.btn_step_del.configure(state=tk.NORMAL if has_step else tk.DISABLED)
        self.btn_step_up.configure(state=tk.NORMAL if has_step else tk.DISABLED)
        self.btn_step_down.configure(state=tk.NORMAL if has_step else tk.DISABLED)

        self.btn_save.configure(state=tk.NORMAL if self.modif else tk.DISABLED)

    def _mark_modified(self):
        self.modif = True
        try:
            self.title(f"Commandes Pas à pas ({self.path_json}) *")
        except Exception:
            pass
        self._refresh_buttons()

    # ---- Handlers commandes ----
    def _on_cmd_select(self, _evt=None):
        idx = self._get_selected_cmd_idx()
        if idx is None:
            return
        cmd = self.commands[idx]
        self.var_name.set(cmd.get("name", ""))
        self.var_spoken.set(cmd.get("spoken", ""))
        self.var_desc.set(cmd.get("description", ""))
        self._load_steps(cmd.get("steps", []))
        self._refresh_buttons()

    def _cmd_add(self):
        new_cmd = {"name": "Nouvelle commande", "spoken": "", "description": "", "steps": []}
        self.commands.append(new_cmd)
        self._load_commands()
        last = len(self.commands) - 1
        self.tree_cmd.selection_set(str(last))
        self.tree_cmd.see(str(last))
        self._mark_modified()

    def _cmd_duplicate(self):
        idx = self._get_selected_cmd_idx()
        if idx is None:
            return
        src = self.commands[idx]
        dup = json.loads(json.dumps(src))  # deep copy
        dup["name"] = (src.get("name") or "") + "_copy"
        self.commands.append(dup)
        self._load_commands()
        self.tree_cmd.selection_set(str(len(self.commands) - 1))
        self._mark_modified()

    def _cmd_delete(self):
        idx = self._get_selected_cmd_idx()
        if idx is None:
            return
        if not messagebox.askyesno("Suppression", "Supprimer la commande sélectionnée ?", parent=self):
            return
        del self.commands[idx]
        self._load_commands()
        self.tree_steps.delete(*self.tree_steps.get_children())
        self.var_name.set("")
        self.var_spoken.set("")
        self.var_desc.set("")
        self._mark_modified()

    def _cmd_update(self):
        idx = self._get_selected_cmd_idx()
        if idx is None:
            messagebox.showwarning("Modification", "Sélectionne une commande.")
            return
        name = self.var_name.get().strip()
        if not name:
            messagebox.showerror("Commande", "Le nom est obligatoire.")
            return
        spoken = self.var_spoken.get().strip()
        desc = self.var_desc.get().strip()
        self.commands[idx].update({"name": name, "spoken": spoken, "description": desc})
        self._load_commands()
        self.tree_cmd.selection_set(str(idx))
        self._mark_modified()

    # ---- Handlers steps ----
    def _step_add(self):
        cmd_idx = self._get_selected_cmd_idx()
        if cmd_idx is None:
            messagebox.showwarning("Étapes", "Sélectionne d'abord une commande.")
            return
        # noms pour execute_command
        names = [c.get("name", "") for c in self.commands if c.get("name")]
        dlg = StepEditor(self, step=None, command_names=names)
        self.wait_window(dlg)
        if dlg.result:
            self.commands[cmd_idx].setdefault("steps", []).append(dlg.result)
            self._load_steps(self.commands[cmd_idx]["steps"])
            self._mark_modified()

    def _step_edit(self):
        cmd_idx = self._get_selected_cmd_idx()
        st_idx = self._get_selected_step_idx()
        if cmd_idx is None or st_idx is None:
            return
        step = self.commands[cmd_idx].get("steps", [])[st_idx]
        names = [c.get("name", "") for c in self.commands if c.get("name")]
        dlg = StepEditor(self, step=step, command_names=names)
        self.wait_window(dlg)
        if dlg.result:
            self.commands[cmd_idx]["steps"][st_idx] = dlg.result
            self._load_steps(self.commands[cmd_idx]["steps"])
            self._mark_modified()

    def _step_delete(self):
        cmd_idx = self._get_selected_cmd_idx()
        st_idx = self._get_selected_step_idx()
        if cmd_idx is None or st_idx is None:
            return
        if not messagebox.askyesno("Suppression", "Supprimer l'étape sélectionnée ?", parent=self):
            return
        del self.commands[cmd_idx]["steps"][st_idx]
        self._load_steps(self.commands[cmd_idx]["steps"])
        self._mark_modified()

    def _step_move(self, delta: int):
        cmd_idx = self._get_selected_cmd_idx()
        st_idx = self._get_selected_step_idx()
        if cmd_idx is None or st_idx is None:
            return
        steps = self.commands[cmd_idx].get("steps", [])
        j = st_idx + delta
        if j < 0 or j >= len(steps):
            return
        steps[st_idx], steps[j] = steps[j], steps[st_idx]
        self._load_steps(steps)
        self.tree_steps.selection_set(str(j))
        self.tree_steps.see(str(j))
        self._mark_modified()

    def _on_step_double_click(self, event):
        """Double-clic sur une ligne des étapes → ouvrir la modale Modifier."""
        region = self.tree_steps.identify("region", event.x, event.y)
        if region not in ("cell", "tree"):
            return
        row_id = self.tree_steps.identify_row(event.y)
        if not row_id:
            return
        self.tree_steps.selection_set(row_id)
        self._step_edit()

    # ---- Fichier ----
    def _action_load(self):
        if self.modif:
            res = messagebox.askyesnocancel("Enregistrer ?",
                                            "Enregistrer les modifications avant d'ouvrir un autre fichier ?",
                                            parent=self)
            if res is None:
                return
            if res:
                self._save()
        path = filedialog.askopenfilename(parent=self, title="Ouvrir un fichier pas à pas",
                                          filetypes=[("JSON", "*.json"), ("Tous fichiers", "*.*")])
        if not path:
            return
        self.path_json = path
        self.commands = _load_pp(self.path_json)
        self._load_commands()
        self.lbl_file.configure(text=f"Fichier : {self.path_json}")
        self.modif = False
        self.title(f"Commandes Pas à pas ({self.path_json})")

    def _action_save_as(self):
        path = filedialog.asksaveasfilename(parent=self, title="Enregistrer sous",
                                            defaultextension=".json",
                                            filetypes=[("JSON", "*.json"), ("Tous fichiers", "*.*")])
        if not path:
            return
        self.path_json = path
        self._save()
        self.lbl_file.configure(text=f"Fichier : {self.path_json}")

    def _sync_form_into_selected(self):
        """Recopie les champs du formulaire (Nom/Spoken/Description)
        dans la commande sélectionnée, sans afficher d'alerte.
        Utilisé avant l'enregistrement pour éviter d'oublier 'Mettre à jour'.
        """
        idx = self._get_selected_cmd_idx()
        if idx is None:
            return
        name = self.var_name.get().strip()
        spoken = self.var_spoken.get().strip()
        desc = self.var_desc.get().strip()
        if name:  # on ne force pas si vide
            self.commands[idx].update({"name": name, "spoken": spoken, "description": desc})
            # rafraîchir la ligne correspondante dans la liste
            try:
                self.tree_cmd.item(str(idx), values=(name, spoken, desc))
            except Exception:
                pass

    def _save(self):
        self._sync_form_into_selected()
        _save_pp(self.commands, self.path_json)
        self.modif = False
        self.title(f"Commandes Pas à pas ({self.path_json})")
        # Optionnel: recharger dynamiquement l'exécuteur si présent dans l'app
        try:
            if self.app is not None and hasattr(self.app, "pp_executor"):
                # pp_registry/executor basés sur current_mode (comme tu l'as fait)
                app_root = getattr(self.app, "app", None) or self.app  # selon où on stocke config
                # on retrouve le mode courant pour l'executor
                current_mode = getattr(app_root, "current_mode", self.app)
                app_root.pp_executor = Executor(current_mode, self.path_json)
                update_status_bar(getattr(current_mode, "status_bar", None),
                                  text=f"{app_root.pp_executor.path_json} rechargé",
                                  bg="lightblue", fg="darkblue", anchor="w")
        except Exception:
            pass
        self._refresh_buttons()

    # ---- fermeture ----
    def _on_close(self):
        if self.modif:
            if messagebox.askyesno("Fermer", "Enregistrer les modifications avant de fermer ?"):
                self._save()
        if callable(self.termine_cb):
            try:
                self.termine_cb(self.path_json)
            except Exception:
                pass
        self.destroy()


# ---- lancement manuel (debug) ----
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    FenetrePasAPas(root, app=None, path_json="pas_a_pas.json")
    root.mainloop()
