import time
from pynput.keyboard import Controller, Key


class Simulator:
    def __init__(self):
        self.keyboard = Controller()
        self.previous_text = ""
        self.running = False

    def init(self):
        self.previous_text = ""

    def animate_typing (self, new_text:str):
            print(f"On me demande d'écrire : [{new_text}]")
            print(f"j'ai en mémoire : [{self.previous_text}]")
            def find_common_prefix(s1, s2):
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
                time.sleep(0.02)

            new_part = new_text[common_prefix_length:]
            for char in new_part:
                self.type_character(char)
                time.sleep(0.02)  # Add a small delay to simulate typing speed
            
            self.previous_text = new_text

    def type_character(self, char:str):
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