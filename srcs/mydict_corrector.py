# mydict_corrector.py
from __future__ import annotations
import json
import os
import re
import unicodedata
from typing import Any, Dict, List
from utils_window import get_config_path

# Seuil global pour déclencher une correction (0..1)
THRESHOLD = 0.82
# Pondérations
ALPHA_ORTH = 0.6
BETA_PHON = 0.3
GAMMA_WEIGHT = 0.1

# --- Cache + mtime ---
_DICT_CACHE: Dict[str, Any] | None = None
_DICT_MTIME: float | None = None

# --- AJOUTS : passe "from" dure, avec variantes espace/tiret/apostrophe ---
_SEP_CLASS = r"[\s\-\u2019']+"  # espace(s), -, apostrophes droites/typographiques


def invalidate_dict_cache() -> None:
    """Permet de forcer le rechargement au prochain appel."""
    global _DICT_CACHE, _DICT_MTIME
    _DICT_CACHE = None
    _DICT_MTIME = None


def _build_from_regex(bad: str) -> str:
    """
    Construit une regex robuste pour 'bad'.
    - Si 'bad' contient des séparateurs (espace/tiret/apostrophe), on accepte n'importe
      quel séparateur équivalent entre les morceaux.
    - Sinon, on matche le mot tel quel.
    On encadre avec \\b pour éviter d'attraper des sous-parties de mots.
    """
    parts = re.split(r"[\s\-\u2019']+", bad.strip())
    parts = [re.escape(p) for p in parts if p]
    if len(parts) == 0:
        return None
    if len(parts) == 1:
        pat = parts[0]
    else:
        pat = _SEP_CLASS.join(parts)
    return r"\b" + pat + r"\b"


def _hard_replace_from(text: str, entries: List[Dict[str, Any]]) -> str:
    """
    Remplacements 'durs' : si un 'from' apparait, on remplace directement par word.
    Insensible à la casse, respecte la casse du match d'origine (ALLCAPS / Capitalized).
    """
    def _case_preserving_sub(match: re.Match, target: str) -> str:
        s = match.group(0)
        return _preserve_case(s, target)

    # On applique séquentiellement chaque 'from' trouvé.
    # Pour plus d'efficacité, on pourrait compiler tous les patterns au chargement,
    # mais pour un POC c'est suffisant.
    for e in entries:
        word = e.get("word", "")
        for bad in (e.get("from", []) or []) + (e.get("aliases", []) or []):
            pat = _build_from_regex(bad)
            if not pat:
                continue
            text = re.sub(pat, lambda m: _case_preserving_sub(m, word), text, flags=re.IGNORECASE)
    return text


# -------- Utils texte --------
_word_re = re.compile(r"\w+([’'-]\w+)*", re.UNICODE)  # garde mots + tirets/apostrophes


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def _normalize(s: str) -> str:
    s = s.strip().lower()
    s = _strip_accents(s)
    # normalisation des tirets et apostrophes
    s = s.replace("’", "'").replace("`", "'").replace("ʼ", "'")
    s = s.replace("-", "")
    s = s.replace("'", "")
    return s


def _consonant_skeleton(s: str) -> str:
    """Très simple 'clé phonétique' : enlève voyelles après normalisation."""
    s = _normalize(s)
    return re.sub(r"[aeiouy]", "", s)


def _normalized_levenshtein(a: str, b: str) -> float:
    """Retourne une similarité 0..1 (1 = identique)."""
    a, b = _normalize(a), _normalize(b)
    if not a and not b:
        return 1.0
    # DP classique
    la, lb = len(a), len(b)
    dp = list(range(lb + 1))
    for i in range(1, la + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, lb + 1):
            cur = dp[j]
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[j] = min(dp[j] + 1,      # deletion
                        dp[j - 1] + 1,  # insertion
                        prev + cost)    # substitution
            prev = cur
    dist = dp[lb]
    return 1.0 - (dist / max(la, lb))


def _phon_similarity(a: str, b: str) -> float:
    """Similarité naïve via squelette consonantique (0..1)."""
    ka, kb = _consonant_skeleton(a), _consonant_skeleton(b)
    return _normalized_levenshtein(ka, kb)


def _preserve_case(src: str, repl: str) -> str:
    """Préserve la casse basique du token source : majuscules initiales / ALL CAPS."""
    if src.isupper():
        return repl.upper()
    if src and src[0].isupper() and src[1:].islower():
        return repl.capitalize()
    return repl


# -------- Chargement du dictionnaire --------
def _load_dict(path: str) -> Dict[str, Any]:
    """Charge le JSON si nécessaire, sinon rend le cache (hot‑reload par mtime)."""
    global _DICT_CACHE, _DICT_MTIME

    if not os.path.isabs(path) and not os.path.exists(path):
        path = get_config_path(path)

    # 1) si le fichier existe, regarde son mtime
    current_mtime = None
    try:
        current_mtime = os.path.getmtime(path)
    except Exception:
        # pas de fichier : cache vide stable
        if _DICT_CACHE is None:
            _DICT_CACHE = {"lang": "fr_FR", "entries": []}
            _DICT_MTIME = None
        return _DICT_CACHE

    # 2) si mtime a changé (ou pas de cache), recharge
    if _DICT_CACHE is None or _DICT_MTIME != current_mtime:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {"lang": "fr_FR", "entries": []}

        data.setdefault("entries", [])
        for e in data["entries"]:
            e.setdefault("from", e.get("aliases", []))  # compat
            e.setdefault("phonemes", [])
            e.setdefault("weight", 1.0)
            e.setdefault("tags", [])

        _DICT_CACHE = data
        _DICT_MTIME = current_mtime

    return _DICT_CACHE


def _best_alias(e: Dict[str, Any]) -> List[str]:
    # On compare contre le mot canonique + ses aliases
    base = [e.get("word", "")]
    return [x for x in (base + e.get("from", [])) if x]


# -------- Correction principale --------
def correct_with_dict(text: str, path_dico: str = "my.dic") -> str:
    """
    Corrige les mots du texte si une entrée du dico est suffisamment similaire.
    POC : matching orthographique + 'phonétique' léger (squelette consonantique).
    """
    # print(f"correct_with_dict de '{text}' -> ", end='')
    dic = _load_dict(path_dico)
    entries = dic.get("entries", [])
    if not entries or not text or not text.strip():
        return text

    # 1) Passe dure: remplace explicitement les formes 'from' (multi-mots ok)
    text = _hard_replace_from(text, entries)

    # 2) Passe soft: similarité (POC actuel)
    out = []
    last = 0
    for m in _word_re.finditer(text):
        out.append(text[last:m.start()])
        token = m.group(0)
        replacement = _maybe_replace(token, entries)
        out.append(replacement or token)
        last = m.end()
    out.append(text[last:])
    # print(f"[{out}]")
    return "".join(out)


def _maybe_replace(token: str, entries: List[Dict[str, Any]]) -> str | None:
    raw = token
    # ignore très petits tokens / purement numériques
    if len(_normalize(raw)) < 3 or _normalize(raw).isdigit():
        return None

    best_word = None
    best_score = 0.0

    for e in entries:
        weight = float(e.get("weight", 1.0))
        for cand in _best_alias(e):
            s_orth = _normalized_levenshtein(raw, cand)
            s_phon = _phon_similarity(raw, cand)
            score = ALPHA_ORTH * s_orth + BETA_PHON * s_phon + GAMMA_WEIGHT * min(weight, 3.0)
            if score > best_score:
                best_score = score
                best_word = e.get("word")

    if best_word and best_score >= THRESHOLD:
        return _preserve_case(raw, best_word)
    return None
