import string
import enchant
import re


def corriger_texte(texte: str) -> str:
    """
    Corrige automatiquement les mots mal orthographiés si une seule suggestion est trouvée.

    Args:
        texte (str): Texte à corriger.

    Returns:
        str: Texte corrigé.
    """

    dico = enchant.Dict("fr_FR")
    # Séparer le contenu en mots
    mots = re.findall(r'\b[\w-]+\b', texte)  # Prend en compte les mots composés avec des traits d'union

    texte_corrige = texte  # Crée une copie du texte original pour les corrections
    offset = 0  # Utilisé pour ajuster les indices après chaque correction

    for mot in mots:
        # Nettoyer le mot de la ponctuation en début et fin, sans modifier l'original
        mot_nettoye = mot.strip(string.punctuation)

        # Vérifier chaque mot
        if mot_nettoye and not dico.check(mot_nettoye):
            # Obtenir les suggestions
            suggestions = dico.suggest(mot_nettoye)

            # Si une seule suggestion est disponible et l'option auto est activée, remplacer automatiquement le mot
            if len(suggestions) == 1:
                correct_mot = suggestions[0]

                # Calculer les positions dans le texte corrigé en utilisant l'offset
                start_idx = texte_corrige.find(mot, offset)
                end_idx = start_idx + len(mot)

                # Remplacer le mot incorrect par le mot correct
                texte_corrige = texte_corrige[:start_idx] + correct_mot + texte_corrige[end_idx:]

                # Ajuster l'offset pour prendre en compte la différence de longueur
                offset += len(correct_mot) - len(mot)

    return texte_corrige
