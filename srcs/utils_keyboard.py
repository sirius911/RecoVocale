import time
from pynput.keyboard import Controller, Key
from typing import Union, List


TIME_WRITE = 0.001  # delay for typing speed of all Char
TIME_DELETE = 0.01  # delay for typing speed for backspace

# Touches qui peuvent etre maintenues
hold_key = [Key.ctrl, Key.ctrl_l, Key.ctrl_r, Key.shift, Key.shift_l, Key.shift_r,
            Key.alt, Key.alt_l, Key.alt_r, Key.alt_gr]

key_display_names = {
    '\n': 'Entrée',
    ' ': 'Espace',
    '\t': 'Tabulation',
    '\u0001': 'Ctrl',
    '\u0002': 'Flèche gauche',
    '\u0003': 'Flèche droite',
    '\u0004': 'Flèche haut',
    '\u0005': 'Flèche bas',
    '\u0006': 'Suppr',
    Key.ctrl: 'Ctrl',
    Key.left: 'Flèche gauche',
    Key.right: 'Flèche droite',
    Key.up: 'Flèche haut',
    Key.down: 'Flèche bas',
    Key.delete: 'Suppr',
    Key.backspace: 'Retour arrière',
    Key.enter: 'Entrée',
    Key.tab: 'Tabulation',
}


class Simulator:
    """
    Simule des frappes clavier en utilisant la bibliothèque `pynput`.

    Cette classe permet :
    - de taper un texte caractère par caractère,
    - de maintenir certaines touches comme Ctrl, Shift, etc.,
    - de simuler des séquences complexes (ex: Ctrl+V, flèches...),
    - d'animer la saisie en comparant deux états de texte.

    Attributes:
        keyboard (Controller): Contrôleur clavier de `pynput`.
        previous_text (str): Dernier texte tapé, pour comparaison.
        debug (bool): Active ou non les impressions de débogage.
        pressed_key (list): Pile des touches actuellement maintenues.
    """

    def __init__(self, data=List[Union[Key, str]] | None, debug=False):
        """
        Initialise le simulateur clavier. Exécute immédiatement une séquence si `data` est fournie.

        Args:
            data (list[Key | str] | None): Liste de touches à simuler immédiatement.
            debug (bool): Active le mode débogage si True.
        """

        self.keyboard = Controller()
        self.previous_text = ""
        self.debug = debug
        self.pressed_key = []  # stack de touches pressées et non relachées
        self.special_keys_mapping = {
            '\n': Key.enter,
            ' ': Key.space,
            '\t': Key.tab,
            '\u0001': Key.ctrl,  # '\u0001' as a placeholder for Ctrl
            '\u0002': Key.left,  # '\u0002' as a placeholder for Left Arrow
            '\u0003': Key.right,  # '\u0003' as a placeholder for Right Arrow
            '\u0004': Key.up,  # '\u0004' as a placeholder for Up Arrow
            '\u0005': Key.down,  # '\u0005' as a placeholder for Down Arrow
            '\u0006': Key.delete,  # '\u0006' as a placeholder for delete
        }

        if data is not None:    # Permet d'appeler la classe de n'importe ou et de faire taper text
            self.simule_key(data)

    def init(self):
        self.previous_text = ""

    def animate_typing(self, new_text: str):
        """
        Simule la frappe du `new_text` en supprimant les différences avec le texte précédent.

        Args:
            new_text (str): Texte à écrire, modifié dynamiquement.
        """

        def find_common_prefix(s1, s2):
            # fonction renvoyant le nombre de caractère commun entre s1 et s2
            common_prefix_length = 0
            for c1, c2 in zip(s1, s2):
                if c1 != c2:
                    break
                common_prefix_length += 1
            return common_prefix_length

        common_prefix_length = find_common_prefix(self.previous_text, new_text)
        for _ in range(len(self.previous_text) - common_prefix_length):
            self.keyboard.press(Key.backspace)
            self.keyboard.release(Key.backspace)
            time.sleep(TIME_DELETE)

        new_part = new_text[common_prefix_length:]
        self.simule_key(new_part)
        self.previous_text = new_text

    def simule_key(self, input_data: List[Union[Key, str]]) -> None:
        """
        Simule la frappe d’une séquence de touches.

        Args:
            input_data (list): Liste de caractères ou de touches spéciales (`Key`).
        """

        for item in input_data:
            if isinstance(item, Key) and item in hold_key:  # touche à maintenir
                # print(f"Key = {item}")
                self.keyboard.press(item)  # On reste appuyé
                self.pressed_key.append(item)
                # print(f"push1 [{item}]")
            elif isinstance(item, str):
                # print(f"simule : {item}")
                self._type_character(item)
            else:
                self.keyboard.tap(item)
        # On vide la stack des touches qui doivent être maintenues
        # print(f"nb touche appuyée = {len(self.pressed_key)}")
        while len(self.pressed_key) > 0:
            release_key = self.pressed_key.pop()
            self.keyboard.release(release_key)  # On relache
            # print(f" Release [{release_key}]")

    def _type_character(self, char: str):
        """
        Tape un caractère ou une chaîne de texte.
        Si c'est une touche spéciale mappée, on envoie la Key correspondante.
        Sinon, si la chaîne a plusieurs caractères, on la tape lettre par lettre.
        """
        key = self.special_keys_mapping.get(char, None)

        # touche spéciale via mapping (ex: '\n', '\t', ...)
        if key is not None:
            if key in hold_key:
                self.keyboard.press(key)
                self.pressed_key.append(key)
            else:
                self.keyboard.tap(key)
            return

        # ici 'char' est du texte ordinaire
        if len(char) == 1:
            self.keyboard.tap(char)
        else:
            for ch in char:
                self.keyboard.tap(ch)
                time.sleep(TIME_WRITE)

    @staticmethod
    def parse_keys(seq):
        """
        Transforme une liste en séquence Key/str.
        Accepte:
          ["{TAB}", "{ENTER}"]
          ["{TAB}{ENTER}"]
          ["Salut{ENTER}", "{CTRL}", "v"]
        """
        import re
        mapping = {
            "{ENTER}": Key.enter, "{TAB}": Key.tab, "{ESC}": Key.esc,
            "{DEL}": Key.delete, "{DELETE}": Key.delete, "{BACKSPACE}": Key.backspace,
            "{UP}": Key.up, "{DOWN}": Key.down, "{LEFT}": Key.left, "{RIGHT}": Key.right,
            "{CTRL}": Key.ctrl, "{ALT}": Key.alt, "{SHIFT}": Key.shift, "{SPACE}": " ",
        }
        token_re = re.compile(r"\{[A-Za-z_]+\}")

        out = []
        for item in seq:
            if isinstance(item, Key):
                out.append(item)
                continue
            s = str(item)
            pos = 0
            for m in token_re.finditer(s):
                # texte avant le token
                if m.start() > pos:
                    out.append(s[pos:m.start()])
                tok = m.group().upper()
                out.append(mapping.get(tok, tok))  # inconnu => on tape le texte "{...}"
                pos = m.end()
            # suffixe après le dernier token
            if pos < len(s):
                out.append(s[pos:])
        return out
