from __future__ import annotations
import ctypes
import time
import re
from ctypes import wintypes
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import threading
import json
import shlex
from utils_window import get_config_path
from utils_keyboard import Simulator
# on réutilise tes actions existantes
from Actions import Run as RunAction, Attendre as AttendreAction, Keyboard as KeyboardAction


# ---------- Modèle ----------
class StepType(str, Enum):
    OPEN_APP = "open_app"        # Ouvrir l'application
    WAIT = "wait"                # Attente en ms
    SEND_KEYS = "send_keys"      # Envoi de touches (ajouté à l'étape 3)
    WAIT_WINDOW = "wait_window"  # Attendre l'ouverture d'une fenêtre (étape 4)
    EXECUTE_COMMAND = "execute_command"  # Appel d'une autre commande (étape 5)


@dataclass
class Step:
    type: StepType
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Command:
    name: str
    spoken: str                 # Forme prononcée
    description: str = ""
    steps: List[Step] = field(default_factory=list)


# ---------- Registre ----------
def _norm(s: str) -> str:
    return " ".join(s.lower().strip().split())


class CommandRegistry:
    def __init__(self) -> None:
        self.by_name: Dict[str, Command] = {}
        self.by_spoken: Dict[str, str] = {}

    def add(self, cmd: Command) -> None:
        self.by_name[cmd.name] = cmd
        self.by_spoken[_norm(cmd.spoken)] = cmd.name

    def get_by_spoken(self, spoken: str) -> Optional[Command]:
        return self.by_name.get(self.by_spoken.get(_norm(spoken), ""))


# ---------- Chargement JSON ----------
def load_registry_from_json(path: str) -> CommandRegistry:
    with open(get_config_path(path), "r", encoding="utf-8") as f:
        raw = json.load(f)

    reg = CommandRegistry()
    for obj in raw:
        steps = [Step(StepType(s["type"]), s.get("params", {})) for s in obj.get("steps", [])]
        reg.add(Command(
            name=obj["name"],
            spoken=obj["spoken"],
            description=obj.get("description", ""),
            steps=steps
        ))
    return reg


# --- helpers fenêtre (Win32 via ctypes) ---
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)


def _get_window_text(hwnd: int) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def _get_class_name(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def _is_window_visible(hwnd: int) -> bool:
    return bool(user32.IsWindowVisible(hwnd))


def _get_pid(hwnd: int) -> int:
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def wait_for_window(
    title_contains: str | None = None,
    title_regex: str | None = None,
    class_name: str | None = None,
    pid: int | None = None,
    timeout_ms: int = 10000,
    require_visible: bool = True,
    activate: bool = False,
) -> bool:
    """Attend qu'une fenêtre correspondant aux critères apparaisse."""
    deadline = time.time() + (timeout_ms / 1000.0)
    regex = re.compile(title_regex, re.I) if title_regex else None
    found_hwnd = None

    def enum_cb(hwnd, lparam):
        nonlocal found_hwnd
        if require_visible and not _is_window_visible(hwnd):
            return True
        if class_name and _get_class_name(hwnd) != class_name:
            return True
        if pid is not None and _get_pid(hwnd) != pid:
            return True

        title = _get_window_text(hwnd)
        if title_contains and title_contains.lower() not in title.lower():
            pass
        elif regex and not regex.search(title):
            pass
        else:
            found_hwnd = hwnd
            return False  # stop EnumWindows
        return True  # continue

    while time.time() < deadline:
        user32.EnumWindows(EnumWindowsProc(enum_cb), 0)
        if found_hwnd:
            if activate:
                SW_RESTORE = 9
                user32.ShowWindow(found_hwnd, SW_RESTORE)
                user32.SetForegroundWindow(found_hwnd)
            return True
        time.sleep(0.1)
    return False


# ---------- Exécuteur ----------
def _parse_args(args: Any) -> List[str]:
    if args is None:
        return []
    if isinstance(args, list):
        return [str(a) for a in args]
    # robust sur Windows : posix=False
    return shlex.split(str(args), posix=False)


class Executor:
    def __init__(self, app, registry: CommandRegistry) -> None:
        self.app = app
        self.registry = registry

    def run_by_spoken(self, spoken_text: str) -> bool:
        """Retourne True si une commande a été trouvée et lancée en thread."""
        cmd = self.registry.get_by_spoken(spoken_text)
        if not cmd:
            return False
        threading.Thread(target=self._run, args=(cmd,), daemon=True).start()
        return True

    # --- interne ---
    def _run(self, cmd: Command) -> None:
        for step in cmd.steps:
            self._exec_step(step)

    def _exec_step(self, step: Step) -> None:
        t = step.type
        p = step.params

        if t == StepType.OPEN_APP:
            target = p["target"]                      # ex: r"C:\...\iexplore.exe"
            args = _parse_args(p.get("args", ""))     # ex: "https://..." ou liste
            mode = p.get("window", "normal")          # "normal" | "maximized" | "minimized"
            RunAction(self.app, target, args, window_mode=mode).execute()

        elif t == StepType.WAIT:
            ms = int(p.get("ms", 0))
            AttendreAction(self.app, ms/1000.0).execute()

        elif t == StepType.SEND_KEYS:
            raw = p.get("keys", [])
            try:
                keys = Simulator.parse_keys(raw)
            except Exception:
                keys = raw  # fallback
            KeyboardAction(self.app, keys).execute()

        elif t == StepType.EXECUTE_COMMAND:
            name = p["name"]
            nested = self.registry.by_name.get(name)
            if nested:
                self._run(nested)

        elif t == StepType.WAIT_WINDOW:
            ok = wait_for_window(
                title_contains=p.get("title_contains"),
                title_regex=p.get("title_regex"),
                class_name=p.get("class_name"),
                pid=p.get("pid"),
                timeout_ms=int(p.get("timeout_ms", 10000)),
                require_visible=bool(p.get("require_visible", True)),
                activate=bool(p.get("activate", True)),
            )
            if not ok:
                print("[PasÀPas] WAIT_WINDOW : timeout")

        elif t == StepType.EXECUTE_COMMAND:
            name = p["name"]
            nested = self.registry.by_name.get(name)
            if nested:
                self._run(nested)
            else:
                print(f"[PasÀPas] EXECUTE_COMMAND : commande introuvable [{name}]")

        else:
            raise ValueError(f"Type d'étape inconnu: {t}")
