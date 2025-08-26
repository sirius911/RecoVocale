import re
from datetime import datetime
from unite import convertir_unites
from mydict_corrector import correct_with_dict

PATTERN_INSERER = (
    r"\bins[éèêe]r(?:é|er|ez|ée|ées|és)\b"   # flexions d'« Insérer » (non capturant)
    r"\s*:?\s*"                              # espaces / « : » optionnel
    r"(?P<contenu>[^\n]*)"                   # contenu jusqu'au saut de ligne
)


def int_to_roman(number: int) -> str:
    """
    Convertit un entier en chiffre romain.

    Args:
        number (int): Un nombre entier entre 1 et 3999.

    Returns:
        str: La représentation en chiffres romains du nombre.
    """
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


def detecter_chiffre_roman(text: str) -> str | None:
    """
    Détecte les expressions du type "chiffre romain" dans le texte
    et retourne leur équivalent en chiffres romains.

    Args:
        text (str): La phrase à analyser.

    Returns:
        str | None: Le chiffre romain trouvé, ou None si rien n'est détecté.
    """
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
        return int_to_roman(int(match_chiffre.group(1))), True

    # Expression régulière pour capturer les nombres en lettres
    pattern_lettres = r"chiffre[s]? roma[i]?n[t]?[s]?\s*(\w+)"

    # Vérifier si un nombre en lettres suit "romain"
    match_lettres = re.search(pattern_lettres, text.lower())
    if match_lettres:
        nombre_en_lettres = match_lettres.group(1)
        # Vérifier si le mot correspond à un nombre dans le dictionnaire
        if nombre_en_lettres in nombres_en_lettres:
            print("[Insérer][CHIFFRE ROMAIN]")
            return int_to_roman(nombres_en_lettres[nombre_en_lettres]), True

    return None, False  # Retourner None si aucun chiffre n'est trouvé


def remplacement_special(text: str):
    """
    Traite les commandes spéciales comme "date" ou "chiffre romain".
    Remplace seulement le mot‑clé, en conservant le reste du texte.
    """
    # Nettoyage minimal (espaces, deux‑points)
    clean = text.lstrip(" :").rstrip()

    # --- gestion de la date ---
    # repère "date" en tout début, puis stocke le reste
    m = re.match(r"(?i)^date\b(.*)", clean)
    if m:
        reste = m.group(1)          # ce qu’il y a après "date"
        date_aujourdhui = datetime.now().strftime("%d/%m/%Y")
        retour = date_aujourdhui + reste   # on recolle le reste inchangé
        return retour, True

    # --- autres cas (ex. chiffre romain) ---
    retour, _insertion = detecter_chiffre_roman(text)
    return retour, _insertion


def remplacer_avec_dictionnaire(
    texte: str, pattern: str, dico_insertion: dict[str, str]
) -> tuple[str, bool]:
    insertion = False

    def remplacement(match: re.Match) -> str:
        nonlocal insertion
        # ⚠️ On lit le groupe NOMMÉ
        contenu = match.group("contenu").rstrip("\r").strip()
        print(f"[Insérer] [{contenu}]", end="")

        # Commandes spéciales d'abord (ex: date, chiffre romain…)
        retour, a_fait = remplacement_special(contenu)
        if retour is not None and a_fait:
            insertion = True
            print(f" -> spécial [{retour}]")
            return retour

        # Puis dictionnaire (regex -> remplacement)
        for regex, subst in dico_insertion.items():
            if re.search(regex, contenu, flags=re.IGNORECASE):
                print(f" -> trouvé [{subst}]")
                insertion = True
                return subst

        # Rien trouvé : on laisse tel quel
        print(" -> non trouvé")
        return match.group(0)

    nouveau = re.sub(pattern, remplacement, texte, flags=re.IGNORECASE | re.MULTILINE)
    return nouveau, insertion


def insertion(phrase: str, dico_insertion: dict[str, str]) -> tuple[str, bool]:
    insertion_effectuee = False

    while True:
        texte_apres, a_change = remplacer_avec_dictionnaire(
            phrase, PATTERN_INSERER, dico_insertion
        )
        insertion_effectuee = insertion_effectuee or a_change
        if not a_change:
            break
        phrase = texte_apres

    return texte_apres, insertion_effectuee


def proteger_points_speciaux(phrases: str) -> str:
    """
    Protège temporairement les expressions contenant 'point(s)' précédées d'articles ou de chiffres
    afin d'éviter leur remplacement automatique.

    Args:
        phrases (str): Le texte à traiter.

    Returns:
        str: Le texte avec les expressions protégées.
    """
    pattern_protection = r"\b(des|les|le|de \d+|les \d+|des \d+|\d+) point[s]?\b"
    # Ajout d'un préfixe et des caractères uniques pour protéger ces éléments -> on efface ensuite
    return re.sub(pattern_protection,
                  lambda match: f"PROTECT_{match.group(0).replace(' ', '_')}",
                  phrases,
                  flags=re.IGNORECASE)


def remplacement_normal(phrases: str) -> str:
    """
    Applique des remplacements classiques dictés oralement dans le texte
    (ex : "point virgule", "ouvrons les guillemets", etc.).

    Args:
        phrases (str): Le texte dans lequel effectuer les remplacements.

    Returns:
        str: Le texte après remplacements.
    """
    expression_remplacement = {
        r"[.,]*tir(ée|é|è|er|et|ez)[., ]*": " - ",
        r"[., ]*trois point[s]? de suspension[s]?[., ]*": "...",
        r"[., ]*3 point[s]? de suspension[s]?[., ]*": "...",
        r"[., ]*3 petit[s]?.": "...", r"[., ]*trois petit[s]?.": "...",
        r"[.,]*ouvr\w*\s+(les\s|le\s)?guillemet[s]?[., ]*": "«",
        r"[.,]*ouvr\w*\s+(la\s|les\s)?parenthèse[s]?[,. ]*": "(",
        r"[.,]*entre guillemet[s]?[,. ]*": "«",
        r"[.,]*entre parenthèse[s]?[,. ]*": "(",
        r"[., ]*ferm\w*\s+(les\s|le\s)?guillemet[s]?[,.]*": "»",
        r"[., ]*ferm\w*\s+(les\s|la\s)?parenthèse[s]?[,.]*": ")",
        r"[., ]*\b(deux|de|2)\b point[s]?[,.]*": ":",
        r"[., ]*point d'interrogation[,.]*": " ? ",
        r"[.,]*point d'exclamation[s]?[,.]*": " ! ",
        r"[., ]*point [àa] la ligne": ".\n",
        r"[., ]*point virgule": "; ",
        r"[., ]*retour [àa] la ligne[,. ]*": "\n",
        r"[., ]*[àa] la ligne": "\n",
        r"[., ]*v[ieè]rgule[,. ]*": ", ",
        r"\bpoint[s]?[,. ]*": ". ",
        r"[., ]*backslash[,. ]*": "\\",
        r"[., ]*sl[aâ](s?ch|sh)[e]?[,. ]*": "/",
        r"[., ]*underscore[,. ]*": "_",
        r"[., ]*arobase[,. ]*": "@",
    }

    # Appliquer les remplacements
    for seq_to_find, substitute in expression_remplacement.items():
        phrases = re.sub(seq_to_find, lambda match: substitute, phrases, flags=re.IGNORECASE)

    return phrases


def restaurer_points_speciaux(phrases: str) -> str:
    """
    Restaure les mots protégés par `proteger_points_speciaux()` dans leur forme originale.

    Args:
        phrases (str): Le texte dans lequel restaurer les points.

    Returns:
        str: Le texte avec les éléments protégés remis en forme.
    """

    # Restaurer les occurrences protégées en supprimant "PROTECT_" et remplaçant les "_" par des espaces
    return re.sub(r"PROTECT_(des|les|le|de_\d+|les_\d+|des_\d+|\d+)_point[s]?",
                  lambda match: match.group(0).replace("PROTECT_", "").replace('_', ' '),
                  phrases, flags=re.IGNORECASE)


def corrige_ponctuation(phrases: str) -> str:
    """
    Corrige la ponctuation dans la phrase selon des règles dictées à l'oral.

    Args:
        phrases (str): Texte à corriger.

    Returns:
        str: Texte corrigé.
    """
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

    # supprimer la ponctuation après le \n
    phrases_finale = re.sub(r'(?<=\n)[.,;:!?]', '',  phrases_finale)

    # 1) Supprimer les espaces avant la ponctuation
    phrases_finale = re.sub(r'\s+([.,;:!?])', r'\1', phrases_finale)

    # 2) Réduire tout doublon de ponctuation, même s'il restait des espaces entre les deux signes
    phrases_finale = re.sub(r'([.,;:!?])(?:\s*\1)+', r'\1', phrases_finale)

    # 3) Nettoyer les espaces autour des sauts de ligne
    phrases_finale = re.sub(r' (?=\n)|(?<=\n) ', '', phrases_finale)

    return phrases_finale


def intercept(phrases: str, dico_insertion: dict[str, str]):
    """
    Intercepte des expressions vocales spécifiques dans une phrase et applique les conversions définies,
    notamment les insertions et les unités.

    Args:
        phrases (str): La phrase dictée.
        dico_insertion (dict[str, str]): Dictionnaire contenant les insertions personnalisées.

    Returns:
        str: La phrase modifiée après traitement.
    """

    '''
    doit intercepter des mots clefs dans une liste de phrase
        retrenvoi la phrase corrigée et un flag  indiquand si on doit terminé la transcription
        insertion: bool True si une insertion a eu lieu
    '''
    _insertion = False
    phrase_interceptee, _insertion = insertion(phrases, dico_insertion)
    resultat = convertir_unites(phrase_interceptee)
    return resultat, _insertion


if __name__ == "__main__":
    dico_insertion = {
        r"\bheure\b": datetime.now().strftime("%H:%M"),
        r"\bbonjour\b": "👋",
    }
    phrase = input("Tapez une phrase : ")
    while True:
        print("1) intercept()")
        print("2) corriger_texte()")
        print("3) corrige_ponctuation()")
        print("4) remplacement_normal()")
        print("5) proteger_points_speciaux()")
        print("5) remplacement_special()")
        print("6) insertion()")
        print("7) int_to_roman()")
        print("8) detecter_chiffre_roman()")
        print("9) remplacer_avec_dictionnaire()")
        print("10) restaurer_points_speciaux()")
        print("11) convertir_unités")
        print("12) changer la phrase")
        print("\n\t0)  -> quitte")

        while True:
            print("Choisissez la fonction a tester : ")
            try:
                choix = int(input(f"\tPour la phrase = [{phrase}] : "))
                break
            except ValueError:
                print("erreur")
        interception = False
        match choix:
            case 1:
                phrase_corrigee, interception = intercept(phrase, dico_insertion)
            case 2:
                phrase_corrigee = correct_with_dict(phrase)
            case 3:
                phrase_corrigee = corrige_ponctuation(phrase)
            case 4:
                phrase_corrigee = remplacement_normal(phrase)
            case 5:
                phrase_corrigee = proteger_points_speciaux(phrase)
            case 6:
                phrase_corrigee, interception = insertion(phrase, dico_insertion)
            case 7:
                num = int(input("Rentrer un Entier : "))
                phrase_corrigee = str(int_to_roman(num))
            case 8:
                phrase_corrigee = str(detecter_chiffre_roman(phrase))
            case 9:
                phrase_corrigee = remplacer_avec_dictionnaire(phrase, dico_insertion)
            case 10:
                phrase_corrigee = restaurer_points_speciaux(phrase)
            case 11:
                phrase_corrigee = convertir_unites(phrase)
            case 12:
                phrase = input("Tapez une nouvelle phrase : ")
                phrase_corrigee = phrase
            case 0:
                break
            case _:
                print("mauvaise commande...")
        modif = (phrase.strip() != phrase_corrigee.strip()) or interception
        print("\n---------------------------------------")
        print(f"phrase origine = {phrase}")
        print(f"après fonction = {phrase_corrigee}{' [⚠️]' if modif else ''}")
        print("\n---------------------------------------")
        phrase = phrase_corrigee
