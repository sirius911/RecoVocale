import re


def convertir_unites(texte: str) -> str:
    """
    Convertit les unités écrites en toutes lettres dans un texte en leurs abréviations normalisées.

    Cette fonction traite également des cas complexes comme :
    - "X unité par Y unité" → "Xunit/Yunit"
    - "5,7 mg par litre" → "5,7mg/L"
    - "comprimé par jour" → "comp./jour"

    Args:
        texte (str): Le texte contenant des unités médicales à convertir.

    Returns:
        str: Le texte avec les unités remplacées par leurs formes abrégées.
    """

    unit_mapping = {
        r"\blitres?\b": "L",
        r"\bdécilitres?\b": "dL",
        r"\bcentilitres?\b": "cL",
        r"\bmillilitres?\b": "mL",
        r"\bmillimètres?\b": "mm",
        r"\bgrammes?\b": "g",
        r"\bmilligrammes?\b": "mg",
        r"\bkilos?\b": "kg",
        r"\bcentimètres? cubes?\b": "cm³",
        r"\bcentimètres? carrés?\b": "cm²",
        r"\bkilomètres?\b": "km",
        r"\bcentimètres?\b": "cm",
        r"\bcomprimés?\b": "comp.",
        r"\bminutes?\b": "min",
        r"\bHB?\b": "Hb",
    }

    # Remplacement direct des unités longues par abréviations
    for pattern, abbr in unit_mapping.items():
        texte = re.sub(pattern, abbr, texte, flags=re.IGNORECASE)

    # Cas 1 : chiffre + unité par chiffre + unité (ex: 16,2g par 100dL)
    texte = re.sub(
        r"(\d+(?:,\d+)?)\s?([a-z²³]+)\s+par\s+(\d+(?:,\d+)?)\s?([a-z²³]+)",
        r"\1\2/\3\4",
        texte,
        flags=re.IGNORECASE,
    )

    # Liste d’unités abrégées utilisées dans les "X par Y"
    unites = r"(?:mg|g|kg|ml|mL|L|l|mm|cm|km|comp\.)"

    # Cas 2 : valeur + unité par unité longue (ex: 5,7 mg par litre → 5,7mg/L)
    texte = re.sub(
        fr"\b(\d+(?:,\d+)?\s?{unites})\b\s+par\s+"
        r"(litres?|décilitres?|centilitres?|millilitres?|heures?|minutes?|secondes?|jour[s]?)\b",
        lambda m: f"{m.group(1).replace(' ', '')}/"
        f"{unit_mapping.get(fr'\\b{m.group(2).lower()}\\b', m.group(2))}",
        texte,
        flags=re.IGNORECASE
    )

    # Cas 3 : unité abrégée par temps (comp./jour, etc.)
    texte = re.sub(
        fr"\b({unites})\b\s+par\s+(jour[s]?|heures?|minutes?|secondes?)\b",
        r"\1/\2",
        texte,
        flags=re.IGNORECASE
    )

    # Cas 4 : sécurité finale, transforme "unité1 par unité2" → "unité1/unité2"
    texte = re.sub(
        r"\b(mg|g|kg|ml|mL|L|l|mm|cm|km|comp\.)\b\s+par\s+\b(dL|cL|mL|L|h|min|s|jour[s]?|décilitres?|litres?)\b",
        lambda m: f"{m.group(1)}/{unit_mapping.get(fr'\\b{m.group(2).lower()}\\b', m.group(2))}",
        texte,
        flags=re.IGNORECASE
    )
    # Cas 5 : nombre seul suivi de "par" + n'importe quelle unité connue
    texte = re.sub(
        r"\b(\d+(?:,\d+)?)\s+par\s+(L?|dL?|cL?|mL?|heures?|min?|s?|secondes?|jour[s]?|g?|mg?|kg?|comp.?|cm?|km?|mm?)\b",
        lambda m: f"{m.group(1)}/{unit_mapping.get(fr'\\b{m.group(2).lower()}\\b', m.group(2))}",
        texte,
        flags=re.IGNORECASE
    )

    return texte


'''
Exemple d'utilisation :
    phrases = [
        "La boîte contient 100 millilitres et 200 grammes de liquide.",
        "16,2 grammes par 100 décilitres",
        "12 centimètres de mèche plus 4 centimètres cubes de 1 litre",
        "16,2 grammes par décilitre 200 Kilos sur 35 centimètres carré.",
        "16,2 grammes par 100 décilitres.",
        "La boîte contient 12 centimètres par 4 centimètres cubes de 1 litre.",
        "16,2 grammes par décilitre.",
        "Sotalol 80 milligramme dose réduite à 1/2 comp. par jour le soir",
        "créatininémie à 5,7 mg par litre",
        "rythme sinusal à 70 par minute",
        "5,7 mg par litre",
        "Un comprimé par jour le soir",
    ]

    for phrase in phrases:
        print(f"{phrase} => {convertir_unites(phrase)}")
'''
