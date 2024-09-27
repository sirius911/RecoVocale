import tkinter as tk

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
    if start_selection < end_selection:
        # Si une sélection est présente, on supprime la sélection et insère à la position start_selection
        texte_depart = texte_depart[:start_selection] + texte_depart[end_selection:]
        pos_curseur = start_selection
        message = message.lower() # essais !! quand on inserre on met en minuscule
        
    # Insérer le message à la position pos_curseur
    nouveau_text = texte_depart[:pos_curseur] + message + texte_depart[pos_curseur:]
    
    # Calculer fin_insertion comme la position juste après l'insertion du message
    fin_insertion = pos_curseur + len(message)
    
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

    def validation(self):
        self.text_box = self.text_box_en_cours
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
        self.text_box = ""
        self.text_box_en_cours = ""
        self.pos_cur = 0
        self.fin_insertion = 0
    
    def get(self) -> str :
        return (self.text_box)
    
    # def supp(self, text_to_del:str):
    #     # todo Simule Del
    #     pass