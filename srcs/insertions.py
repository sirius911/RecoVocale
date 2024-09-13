# Dictionnaire avec des regex comme clés et des chaînes de remplacement comme valeurs
CHAMBRE="""
Patient en décubitus dorsal.

Les bras le long du corps.

Anesthésie locale Xylocaïne 1 %.

Incision au niveau du sillon deltopectoral droit

Dissection d'une belle veine céphalique au niveau du sillon deltopectoral droit.

"""

BILAN_BIO="""
Faire réaliser, à domicile si nécessaire, une prise de sang avec :
 
- NFS
- Ionogramme, urée, créatinine
- TP, TCA
- CRP
- Bilirubine totale et directe
- TGO, TGP
- Gamma GT
- Phosphatases alcalines
- Albumine, pré-albumine
- Calcium, phosphore, magnésium
- ACE
- CA 19. 9
- CA 125
- Alpha-fœtoprotéine"""

FACTEUR="""
Hypertension artérielle : [Pas d'hypertension artérielle | depuis]
Diabète : [Pas de diabète | DNID | diabète gesta]
Tabac : [Pas de tabagisme | arrêt après    années | tabagisme en cours depuis X années]
Alcool : [Moins d'un verre d'alcool par jour| zéro | entre 1 et 3 verres/jour | plus de 3 verres/jour]
"""

ORDONNANCE="""
- MEDISET plaie moyenne 
- Compresses stériles 10*10cm 
- NaCl pipettes 
- Savon doux type CICAPLAST Lavant 
- MEPILEX Border Flex Oval 13.5*16.5cm 
- MEPILEX Border Flex Oval 7.5*9.5cm 

QSP 10 pansements
"""

ORDONNANCE_IDE="""
A réaliser par IDE au domicile, week-end et jours fériés inclus : 

- Soins de cicatrisation mammaire et axillaire gauche, pansements simples tous les 2-3 jours 
Nombre de sites de pansements : 2 
Pour une série de 10 pansements 

Protocole : 
Lavage eau et savon, douche autorisée avant passage IDE 
MEPILEX sur toutes les cicatrices 
Couper les boucles à J10 si toujours présentes
"""

dico_insertion = {
    r"chambre[s]?": CHAMBRE,
    r"Ordonnance[s]? p[ae]nsement[s]?": ORDONNANCE,
    r"facteur de risque[s]?": FACTEUR,
    r"ordonnance soin[s]? IDE": ORDONNANCE_IDE,
    r"bilan biologique": BILAN_BIO
}