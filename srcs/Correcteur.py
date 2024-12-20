from datetime import datetime
import re

def int_to_roman(number:int):
    if not (0 < number < 4000):
        print("Nombre hors des limites (doit être entre 1 et 3999)")
        return str(number)
    roman_numerals = [
        ('M', 1000), ('CM', 900), ('D', 500), ('CD', 400),
        ('C', 100), ('XC', 90), ('L', 50), ('XL', 40),
        ('X', 10), ('IX', 9), ('V', 5), ('IV', 4), ('I', 1)
        ]

    result = []
    for roman, value in roman_numerals:
        while number >= value:
            result.append(roman)
            number -= value

    return ''.join(result)

def detecter_chiffre_roman(text):
    # Dictionnaire pour les nombres en lettres
    nombres_en_lettres = {
        "un": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6,
        "sept": 7, "huit": 8, "neuf": 9, "dix": 10, "onze": 11, "douze": 12, 
        "treize": 13, "quatorze": 14, "quinze": 15, "seize": 16, "dix-sept": 17, 
        "dix-huit": 18, "dix-neuf": 19, "vingt": 20
    }
    # Expression régulière pour capturer les nombres en chiffres
    pattern_chiffre = r"chiffre roma[i]?n[t]?\s*(\d+)"
    
    # Vérifier si un chiffre numérique suit "romain"
    match_chiffre = re.search(pattern_chiffre, text.lower())
    if match_chiffre:
        # Convertir le chiffre capturé en entier
        print("[Insérer][CHIFFRE ROMAIN]")
        return int_to_roman(int(match_chiffre.group(1)))
    
    # Expression régulière pour capturer les nombres en lettres
    pattern_lettres = r"chiffre[s]? roma[i]?n[t]?[s]?\s*(\w+)"
    
    # Vérifier si un nombre en lettres suit "romain"
    match_lettres = re.search(pattern_lettres, text.lower())
    if match_lettres:
        nombre_en_lettres = match_lettres.group(1)
        # Vérifier si le mot correspond à un nombre dans le dictionnaire
        if nombre_en_lettres in nombres_en_lettres:
            print("[Insérer][CHIFFRE ROMAIN]")
            return int_to_roman(nombres_en_lettres[nombre_en_lettres])
    
    return None  # Retourner None si aucun chiffre n'est trouvé

def remplacement_special(text:str):
    retour = None
    if text.lower() == "date":
        print( "[Insérer][DATE]")
        return datetime.now().strftime("%d/%m/%Y")
    retour = detecter_chiffre_roman(text)
    return retour

def remplacer_avec_dictionnaire(texte, pattern, dico_insertion):
    insertion = False
    def remplacement(match):
        nonlocal insertion  # Permet de modifier la variable `insertion` dans la fonction englobante
        # Capture le texte après "insérer" (ce qui inclut plusieurs mots possibles)
        texte_suivant = match.group(2).strip()
        print(f"[Insérer] [{texte_suivant}]", end="")
        retour = remplacement_special(texte_suivant)
        if retour is not None:
            insertion = True
            return retour
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
    return re.sub(pattern, remplacement, texte, flags=re.IGNORECASE)

def insertion(phrase, dico_insertion):

    pattern = r"\bins[éèêe]r(é|ez|er|ée|ées|és)[,. ]+([\w\s]+)"
    
    # match = re.search(pattern, phrase)
    nouveau_texte = remplacer_avec_dictionnaire(phrase, pattern, dico_insertion)
    # print(f"nouvelle phrase = {nouveau_texte}")
    return nouveau_texte

def proteger_points_speciaux(phrases):
    # Protéger les occurrences de "point" ou "points" précédées par des articles ou des chiffres
    pattern_protection = r"\b(des|les|le|de \d+|les \d+|des \d+|\d+) point[s]?\b"
    # Ajout d'un préfixe et des caractères uniques pour protéger ces éléments -> on efface ensuite
    return re.sub(pattern_protection, lambda match: f"PROTECT_{match.group(0).replace(' ', '_')}", phrases, flags=re.IGNORECASE)

def remplacement_normal(phrases):
    expression_remplacement = {
        r"[.,]*tir(ée|é|è|er|et|ez)[., ]*": " - ",
        r"[., ]*trois point[s]? de suspension[s]?[., ]*": "...",
        r"[., ]*3 point[s]? de suspension[s]?[., ]*": "...",
        r"[., ]*3 petit[s]?.": "...",r"[., ]*trois petit[s]?.": "...",
        r"[.,]*ouvr\w*\s+(les\s|le\s)?guillemet[s]?[., ]*": "«",
        r"[.,]*ouvr\w*\s+(la\s|les\s)?parenthèse[s]?[,. ]*": "(",
        r"[.,]*entre guillemet[s]?[,. ]*": "«",
        r"[.,]*entre parenthèse[s]?[,. ]*": "(",
        r"[., ]*ferm\w*\s+(les\s|le\s)?guillemet[s]?[,.]*": "»",
        r"[., ]*ferm\w*\s+(les\s|la\s)?parenthèse[s]?[,.]*": ")",
        r"[., ]*\b(deux|de|2)\b point[s]?[,.]*": ":",
        r"[., ]*point d'interrogation[,.]*": "?",
        r"[.,]*point d'exclamation[s]?[,.]*": "! ",
        r"[., ]*point [àa] la ligne":".\n",
        r"[., ]*point virgule": "; ",
        r"[., ]*retour [àa] la ligne[,. ]*": "\n",
        r"[., ]*[àa] la ligne": "\n",
        r"[., ]*v[ieè]rgule[,. ]*": ", ",
        r"\bpoint[s]?[,. ]*": ". ",
        r"[., ]*backslash[,. ]*": "\\",
        r"[., ]*sl[aâ](s?ch|sh)[e]?[,. ]*": "/",
        r"[., ]*underscore[,. ]*": "_",
        r"[., ]*arobase[,. ]*" : "@",
    }
    
    # Appliquer les remplacements
    for seq_to_find, substitute in expression_remplacement.items():
        phrases = re.sub(seq_to_find, lambda match: substitute, phrases, flags=re.IGNORECASE)
    
    return phrases

def restaurer_points_speciaux(phrases):
    # Restaurer les occurrences protégées en supprimant "PROTECT_" et remplaçant les "_" par des espaces
    return re.sub(r"PROTECT_(des|les|le|de_\d+|les_\d+|des_\d+|\d+)_point[s]?", lambda match: match.group(0).replace("PROTECT_", "").replace('_', ' '), phrases, flags=re.IGNORECASE)


def corrige_ponctuation(phrases:str):
    
    
    # Ponctuations à enlever
    # ponctuations = ".,;:!?"

    # Supprimer les ponctuations tout en conservant la casse
    # soucis car les ponctuation déjà remplacées sont effacées aussi !
    # phrase_sans_ponctuation = ''.join([char for char in phrases if char not in ponctuations])

    # Étape 1: Protéger les cas spéciaux (phrase modifiée)
    phrases_protegee = proteger_points_speciaux(phrases)
    # print("Après protection :", phrases_protegee)

    # Étape 2: Faire les remplacements normaux (phrase modifiée)
    phrases_remplacee = remplacement_normal(phrases_protegee)
    # print("Après remplacement :", phrases_remplacee)

    # Étape 3: Restaurer les cas protégés (phrase finale)
    phrases_finale = restaurer_points_speciaux(phrases_remplacee)
    # print("Phrase finale :", phrases_finale)

    #supprimer la ponctuation après le \n
    phrases_finale = re.sub(r'(?<=\n)[.,;:!?]', '',  phrases_finale)
    # capture deux signes de ponctuation consécutifs et ne garde que le dernier sauf si 3 points
    phrases_finale = re.sub(r'(?<!\.)[.,;:!?]{2}(?!\.)', lambda match: match.group(0)[-1], phrases_finale)
    # Suppression des espaces précédant '.', ',', ';', ':'
    phrases_finale = re.sub(r' +(?=[.,;:])', '', phrases_finale)
    # Supprimer uniquement les espaces avant et après un '\n'
    phrases_finale = re.sub(r' (?=\n)|(?<=\n) ', '', phrases_finale)
    # print(f" Après regex 4 : {phrases_finale}")

    return phrases_finale

def convertir_unites(texte):
    # Mapping des unités françaises vers leurs abréviations
    unit_mapping = {
        r"\blitres\b": "L",
        r"\bdécilitre[s]?\b": "dL",
        r"\bcentilitre[s]?\b":"cL",
        r"\bmillilitres[s]?\b": "mL",
        r"\bmillimètre[s]?\b": "mm",
        r"\bgrammes?\b": "g",
        r"\bmilligrammes?\b": "mg",
        r"\bkilos?\b": "kg",
        r"\bcentimètre[s]? cube[s]?\b": "cm³",
        r"\bcentimètre[s]? carré[s]?\b": "cm²",
        r"\bkilomètre[s]?\b": "km",
        r"\bcentimètre[s]?\b": "cm",

    }

    # Appliquer les remplacements pour chaque unité
    for pattern, abbr in unit_mapping.items():
        texte = re.sub(pattern, abbr, texte, flags=re.IGNORECASE)

    # Remplacer "par" entre deux quantités avec des unités
    texte = re.sub(
        r"(\d+(?:,\d+)?)\s?\b([a-z²³]+)\b\s+par\s+(\d+(?:,\d+)?)\s?\b([a-z²³]+)\b",
        r"\1\2/\3\4",
        texte,
        flags=re.IGNORECASE,
    )

    # Remplacer "par" entre une quantité et une unité seule
    texte = re.sub(
        r"(\d+(?:,\d+)?)\s?\b([a-z²³]+)\b\s+par\s+\b([a-z²³]+)\b",
        r"\1\2/\3",
        texte,
        flags=re.IGNORECASE,
    )

    return texte


def intercept(phrases, dico_insertion):
    '''
    doit intercepter des mots clefs dans une liste de phrase
    renvoi la phrase corrigée et un flag ending indiquand si on doit terminé la transcription
    '''
    phrase_interceptee = insertion(phrases, dico_insertion)
    resultat = convertir_unites(phrase_interceptee)
    return resultat
