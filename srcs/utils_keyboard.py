import time
from pynput.keyboard import Controller, Key
from typing import Union, List

TIME_WRITE = 0.001   #delay for typing speed of all Char 
TIME_DELETE = 0.01  #delay for typing speed for backspace

#Touches qui peuvent etre maintenues
hold_key = [Key.ctrl, Key.ctrl_l, Key.ctrl_r, Key.shift, Key.shift_l, Key.shift_r,\
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
    def __init__(self, data= List[Union[Key, str]] | None, debug=False):
        self.keyboard = Controller()
        self.previous_text = ""
        self.debug = debug
        self.pressed_key = [] # stack de touches pressées et non relachées
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

    def animate_typing (self, new_text:str):
            if self.debug:
                print(f"On me demande d'écrire : [{new_text}]") #debug
                print(f"j'ai en mémoire : [{self.previous_text}]")
            def find_common_prefix(s1, s2):
                #fonction renvoyant le nombre de caractère commun entre s1 et s2
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
        for item in input_data:
            if isinstance(item, Key) and item in hold_key: #touche à maintenir
                # print(f"Key = {item}")
                self.keyboard.press(item) # On reste appuyé
                self.pressed_key.append(item)
                # print(f"push1 [{item}]")
            elif isinstance(item, str): #str
                # print(f"simule : {item}")
                self._type_character(item)
            else:
                self.keyboard.tap(item)
        # On vide la stack des touches qui doivent être maintenues
        # print(f"nb touche appuyée = {len(self.pressed_key)}")
        while len(self.pressed_key) > 0:
                release_key = self.pressed_key.pop()
                self.keyboard.release(release_key) # On relache
                # print(f" Release [{release_key}]")

    def _type_character(self, char:str):
        key = self.special_keys_mapping.get(char, char)
        if isinstance(key, Key) and key in hold_key:
            self.keyboard.press(key) # On reste appuyé
            self.pressed_key.append(key)
            # print(f"push2 [{key}]")
        else:
            self.keyboard.tap(key) # On 'tape' la touche
