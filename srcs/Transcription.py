import tkinter as tk

def first_char_lower(s):
    """
    Convertit uniquement le premier caractère d'une chaîne en minuscule,
    tout en laissant les autres caractères inchangés.

    Args:
        s (str): La chaîne de caractères à modifier.

    Returns:
        str: Une nouvelle chaîne avec le premier caractère en minuscule
             et le reste de la chaîne inchangé. Si la chaîne est vide,
             elle est renvoyée telle quelle.
    """
    return s[:1].lower() + s[1:] if s else s



def _insert_text(texte_depart, message, pos_curseur=0, cur_selec=(0,0)):
    """
    Insert `message` dans `texte_depart` à la position `pos_curseur`.
    Si `start_selection` et `end_selection` existent, il insère le message en effaçant la sélection.
    
    Args:
        texte_depart (str): Le texte d'origine.
        message (str): Le message à insérer.
        pos_curseur (int): Position actuelle du curseur (index global).
        start_selection (int): Début de la sélection (facultatif).
        end_selection (int): Fin de la sélection (facultatif).
    
    Returns:
        tuple: Le texte modifié et la position juste après le texte inséré (fin_insertion).
    """
    start_selection,end_selection = cur_selec
    insertion = start_selection < end_selection
    if insertion:
        # Si une sélection est présente, on supprime la sélection et insère à la position start_selection
        texte_depart = texte_depart[:start_selection] + texte_depart[end_selection:]
        pos_curseur = start_selection
        message = first_char_lower(message) # essais !! quand on insert on met en minuscule
   
    # Insérer le message à la position pos_curseur
    nouveau_text = (texte_depart[:pos_curseur] + ' ' + message + ' ' + texte_depart[pos_curseur:]).strip()
    
    # Calculer fin_insertion comme la position juste après l'insertion du message
    fin_insertion = pos_curseur + len(message) + 2
    
    return nouveau_text, fin_insertion


class Transcription:

    def __init__(self):
        self.text_transcription = ""
        self.text_en_cours = ""
        self.text_box = ""
        self.text_box_en_cours = ""
        self.pos_cur = 0
        self.fin_insertion = 0
        self.cur_selec = (0, 0)
        self.pile = [''] # pour le undo

    def validation(self):
        self.set(self.text_box_en_cours)
        self.text_transcription += self.text_en_cours

    def update(self, message, pos_curseur=0):
        if pos_curseur == -1 :
            # Si pos_curseur est -1, on insère à la fin du texte
            pos_curseur = len(self.text_box)
        else:
            pos_curseur = self.pos_cur
        self.text_box_en_cours, self.fin_insertion = _insert_text(self.text_box,
                                                                  message,
                                                                  pos_curseur,
                                                                  self.cur_selec)
        self.text_en_cours = message
    
    def clear(self):
        self.text_transcription = ""
        self.text_en_cours = ""
        self.set("")
        self.text_box_en_cours = ""
        self.pos_cur = 0
        self.fin_insertion = 0
    
    def get(self) -> str :
        return (self.text_box)
    
    def set(self, text:str):
        self.text_box = text
