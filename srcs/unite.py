import re

def convertir_unites_fr(texte):
    # Mapping des unités françaises vers leurs abréviations
    unit_mapping = {
        r"\bmillilitres[s]?\b": "ml",
        r"\bmillimètre[s]?\b": "mm",
        r"\bgrammes?\b": "g",
        r"\bkilos?\b": "kg",
        r"\blitres?\b": "l",
        r"\bcentimètre[s]? cube[s]?\b": "cm³",
        r"\bcentimètre[s]? carré[s]?\b": "cm²",
        r"\bkilomètre[s]?\b": "km",
        r"\bcentimètre[s]?\b": "cm",
        r"\bdécilitre[s]?\b": "dl",
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

# Exemple d'utilisation
phrases = [
    "La boîte contient 100 millilitres et 200 grammes de liquide.",
    "16,2 grammes par 100 décilitres",
    "12 centimètres de mèche plus 4 centimètres cubes de 1 litre",
    "16,2 grammes par décilitre 200 Kilos sur 35 centimètres carré.",
    "16,2 grammes par 100 décilitres.",
    "La boîte contient 12 centimètres par 4 centimètres cubes de 1 litre.",
    "16,2 grammes par décilitre."
]

for phrase in phrases:
    print(f"{phrase} => {convertir_unites_fr(phrase)}")
