import time
from pynput.keyboard import Controller, Key

TIME_WRITE = 0.02   #delay for typing speed of all Char 
TIME_DELETE = 0.01  #delay for typing speed for backspace

class Simulator:
    def __init__(self, text=None, debug=False):
        self.keyboard = Controller()
        self.previous_text = ""
        self.debug = debug
        if text is not None:    # Permet d'appeler la classe de n'importe ou et de faire taper text
            self.simule_key(text)

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

    def simule_key(self, chaine):
        for char in chaine:
            self._type_character(char)
            time.sleep(TIME_WRITE) # Add a small delay to simulate typing speed

    def _type_character(self, char:str):
        if char == '\n':
            self.keyboard.press(Key.enter)
            self.keyboard.release(Key.enter)
        elif char == ' ':
            self.keyboard.press(Key.space)
            self.keyboard.release(Key.space)
        elif char == '\t':
            self.keyboard.press(Key.tab)
            self.keyboard.release(Key.tab)
        else:
            self.keyboard.type(char)