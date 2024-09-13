import json
import os
import re
from utils_window import get_config_path
import re
from insertions import dico_insertion

def remplacer_avec_dictionnaire(texte, pattern, dico_insertion):
    insertion = False
    def remplacement(match):
        nonlocal insertion  # Permet de modifier la variable `insertion` dans la fonction englobante
        # Capture le texte après "insérer" (ce qui inclut plusieurs mots possibles)
        texte_suivant = match.group(2).strip()
        print(f"[Insérer] [{texte_suivant}]", end="")

        # Vérifie chaque regex du dictionnaire pour voir si elle correspond à une partie du texte suivant
        for regex, remplacement in dico_insertion.items():
            if re.search(regex, texte_suivant, flags=re.IGNORECASE):
                print(f" -> trouvé [{remplacement}]")
                insertion = True
                return remplacement
        
        # Si aucune correspondance, on laisse tel quel
        print(f" -> non trouvé")
        return match.group(0)
    
    # Utilise re.sub pour remplacer les occurrences du pattern
    return re.sub(pattern, remplacement, texte, flags=re.IGNORECASE), insertion

def insertion(phrase):

    pattern = r"\bins[éèêe]r(é|ez|er|ée|ées|és)[,. ]+([\w\s]+)"
    
    # match = re.search(pattern, phrase)
    nouveau_texte, ending = remplacer_avec_dictionnaire(phrase, pattern, dico_insertion)
    # print(f"nouvelle phrase = {nouveau_texte}")
    return nouveau_texte, ending

def intercept(phrases):
    '''
    doit intercepter des mots clefs dans une liste de phrase
    Slash
    renvoi la phrase corrigée et un flag ending indiquand si on doit terminé la transcription
    '''
    # print(f"intercepte '{phrases}'")

    expression_remplacement = {
        r"[.,]*ouvr\w*\s+(les\s|le\s)?guillemet[s]?[., ]*": "«",
        r"[.,]*ouvr\w*\s+(la\s|les\s)?parenthèse[s]?[,. ]*": "(",
        r"[.,]*entre guillemet[s]?[,. ]*": "«",
        r"[.,]*entre parenthèse[s]?[,. ]*": "(",
        r"[., ]*ferm\w*\s+(les\s|le\s)?guillemet[s]?[,.]*": "»",
        r"[., ]*ferm\w*\s+(les\s|la\s)?parenthèse[s]?[,.]*": ")",
        r"[., ]*\b(deux|de|2)\b point[s]?[,.]*": ":",
        r"[., ]*point d'interrogation[,.]*": "?",
        
        r"[.,]*point d'exclamation[s]?[,.]*": "!",
        r"[., ]*point virgule": ";",
        r"[., ]*à la ligne": "\n",
        r"[., ]*v[ieè]rgule[,. ]*": ",",
        r"[., ]*point[,. ]*": ".",
        r"[., ]*sl[aâ][sc]h[e]?[,. ]*": "/",
    }
    
    # Ponctuations à enlever
    # ponctuations = ".,;:!?"

    # Supprimer les ponctuations tout en conservant la casse
    # soucis car les ponctuation déjà remplacées sont effacées aussi !
    # phrase_sans_ponctuation = ''.join([char for char in phrases if char not in ponctuations])
    phrase_sans_ponctuation = phrases

    # Remplacement des expressions sans tenir compte de la casse
    for seq_to_find, substitute in expression_remplacement.items():
        phrase_sans_ponctuation = re.sub(
            seq_to_find, 
            lambda match: substitute, 
            phrase_sans_ponctuation, 
            flags=re.IGNORECASE
        )

    # print(f" Avant regex : {phrase_sans_ponctuation}")
    #supprimer la ponctuation après le \n
    phrases_finale = re.sub(r'(?<=\n)[.,;:!?]', '',  phrase_sans_ponctuation)
    # print(f" Après regex 1 : {phrases_finale}")
    # capture deux signes de ponctuation consécutifs et ne garde que le dernier
    phrases_finale = re.sub(r'([.,;:!?]){2}', lambda match: match.group(0)[-1], phrases_finale)
    # print(f" Après regex 2 : {phrases_finale}")
    # Suppression des espaces précédant '.', ',', ';', ':'
    phrases_finale = re.sub(r' +(?=[.,;:])', '', phrases_finale)
    # print(f" Après regex 3 : {phrases_finale}")
    # Supprimer uniquement les espaces avant et après un '\n'
    phrases_finale = re.sub(r' (?=\n)|(?<=\n) ', '', phrases_finale)
    # print(f" Après regex 4 : {phrases_finale}")

    phrase_renvoyee, ending = insertion(phrases_finale)
    return phrase_renvoyee, ending


class Correcteur:
    def __init__(self):
        """
        A class to apply text corrections based on a set of predefined rules.

        Attributes:
            corrections (list): A list of correction rules loaded from a JSON file.
        """
        self.corrections = []
        config_path = get_config_path("corrections.json")
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                self.corrections = data.get("corrections", [])
                print(f"Load correction {config_path}: {len(self.corrections)}")
        else:
            print(f"No correction file : {config_path}")

    def applique_corrections(self, texte:str) -> str:
        """
        Initialize the Correcteur with a corrections file.

        Args:
            corrections_file (str): The path to the JSON file containing correction rules.
        """
        for correction in self.corrections:
            regex_patterns = correction.get("regex", [])
            replacements = correction.get("new", [])
            actions = correction.get("actions", [])

            for pattern in regex_patterns:
                regex = re.compile(pattern, re.IGNORECASE)
                texte = regex.sub(replacements[0], texte)  # Assuming single replacement for simplicity

            for action in actions:
                if action == "del_prec_virgule":
                    texte = re.sub(r',\s*', ' ', texte)
                elif action == "del_prec_point":
                    texte = re.sub(r'\.\s*', ' ', texte)
        # Ensure there are no extra periods before a newline
        texte = re.sub(r'\.\s*\n', '.\n', texte)
        # Remove extra periods generated by multiple corrections
        texte = re.sub(r'\.\n+', '.\n', texte)

        return texte
