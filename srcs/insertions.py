import os
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from utils_window import get_config_path


class GestionnaireInsertion:
    """
    Classe responsable de la gestion des insertions vocales personnalisées.

    Cette classe permet :
    - de charger les insertions depuis un fichier XML structuré,
    - de lire, modifier ou ajouter des insertions en mémoire,
    - de sauvegarder les modifications dans un format XML conforme.

    Chaque insertion contient :
    - un nom unique (utilisé pour l’identification dans l’interface),
    - une description facultative,
    - une forme prononcée (déclencheur vocal),
    - un corps de texte à insérer.

    Attributes:
        fichier_xml (str): Chemin du fichier XML contenant les insertions.
        data (dict): Dictionnaire des insertions chargées, indexé par la forme prononcée.
    """

    def __init__(self, fichier_xml: str) -> None:
        """
        Initialise le gestionnaire d'insertion à partir d'un fichier XML.

        Args:
            fichier_xml (str): Chemin vers le fichier XML des insertions.
        """

        self.fichier_xml = get_config_path(fichier_xml)
        print(f"Chargement du fichier des insertions -> {self.fichier_xml}")

        # Vérifier si le fichier existe
        if os.path.exists(self.fichier_xml):
            try:
                self.data = self.charger_donnees()
            except ET.ParseError:
                self.data = {}
        else:
            print(f"Absence de {self.fichier_xml}")
            self.data = {}

    def charger_donnees(self) -> dict:
        """
        Charge les insertions depuis le fichier XML.

        Returns:
            dict: Un dictionnaire avec comme clés les phrases prononcées,
                et comme valeurs un sous-dictionnaire contenant nom, description et contenu.
        """

        tree = ET.parse(self.fichier_xml)
        root = tree.getroot()
        namespaces = {'ns': 'http://nuance.com/NAS/AutoTextImport'}
        insertions = {}

        for auto_text in root.findall('ns:SpeechAutoText', namespaces):
            name = auto_text.find('ns:Name', namespaces).text
            description = auto_text.find('ns:Description', namespaces).text
            spoken_phrase = auto_text.find('.//ns:SpokenPhrase/ns:Phrase', namespaces).text
            body = auto_text.find('ns:Body', namespaces).text
            insertions[spoken_phrase] = {'name': name, 'description': description, 'body': body}

        return insertions

    def get(self) -> dict:
        """
        Retourne un dictionnaire des insertions, sans le préfixe 'insérer ' dans les clés.

        Returns:
            dict: Clés = formes prononcées, Valeurs = contenus textuels des insertions.
        """

        # Créer un dictionnaire avec la clé étant la spoken_phrase sans le mot "insérer"
        return {key.replace('insérer ', ''): value['body'] for key, value in self.data.items()}

    def ajouter_insertion(self, name: str, description: str, spoken_phrase: str, body: str) -> None:
        """
        Ajoute une nouvelle insertion au dictionnaire interne si elle n'existe pas déjà.

        Args:
            name (str): Nom de l'insertion.
            description (str): Description de l'insertion.
            spoken_phrase (str): Forme orale associée.
            body (str): Contenu à insérer.
        """

        if spoken_phrase not in self.data:
            self.data[spoken_phrase] = {'name': name, 'description': description, 'body': body}

    def sauvegarder_modifications(self) -> None:
        """
        Sauvegarde toutes les insertions actuelles dans le fichier XML.
        Le fichier est formaté avec indentation et encodé en UTF-8.
        """

        root = ET.Element("SpeechAutoTexts", xmlns="http://nuance.com/NAS/AutoTextImport")

        for spoken_phrase, data in self.data.items():
            auto_text = ET.SubElement(root, "SpeechAutoText")

            # Ajouter les éléments au XML
            ET.SubElement(auto_text, "Format").text = "1"
            ET.SubElement(auto_text, "Name").text = data['name']
            ET.SubElement(auto_text, "Description").text = data.get('description', "")
            ET.SubElement(auto_text, "OwningObjectType").text = "User"
            ET.SubElement(auto_text, "OwningObjectName").text = "BAUFAB"
            ET.SubElement(auto_text, "ProductGuid").text = "5766e812-0b77-4595-9a53-552142261862"
            ET.SubElement(auto_text, "Locale").text = "fr-FR"

            # MetaData
            meta_data_dict = ET.SubElement(auto_text, "MetaDataDictionary")
            meta_data = ET.SubElement(meta_data_dict, "MetaData")
            ET.SubElement(meta_data, "Name").text = "DNS_PlainText"
            ET.SubElement(meta_data, "Value").text = "1"

            # SpokenPhrases
            spoken_phrases = ET.SubElement(auto_text, "SpokenPhrases")
            spoken_phrase_elem = ET.SubElement(spoken_phrases, "SpokenPhrase")
            ET.SubElement(spoken_phrase_elem, "Phrase").text = spoken_phrase

            # Body with correct line breaks
            body_element = ET.SubElement(auto_text, "Body")
            body_element.text = data['body']

        # Sauvegarde avec formatage propre
        xml_str = ET.tostring(root, encoding="utf-8")
        pretty_xml_str = minidom.parseString(xml_str).toprettyxml(indent="  ")

        # Écriture dans le fichier avec sauts de ligne et encodage utf-8
        with open(self.fichier_xml, "w", encoding="utf-8") as f:
            f.write(pretty_xml_str)
