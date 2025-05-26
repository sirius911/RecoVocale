import os
import time
import tkinter as tk
import tkinter.font as tkFont
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from tkinter import messagebox

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


class FenetreGestion(tk.Toplevel):
    """
    Interface graphique permettant de visualiser, ajouter, modifier ou supprimer
    des insertions vocales définies dans un fichier XML.

    Cette fenêtre modale s'appuie sur un `GestionnaireInsertion` pour manipuler les données,
    et propose une interface utilisateur simple avec champs de saisie, liste d'insertions,
    et boutons d'action.

    Args:
        parent (tk.Widget): Fenêtre parent.
        gestionnaire (GestionnaireInsertion): Objet de gestion des insertions.
        termine (Callable | None): Fonction à appeler lors de la fermeture de la fenêtre.
    """

    def __init__(self, parent: tk.Tk, gestionnaire: GestionnaireInsertion, termine=None) -> None:
        """
        Initialise la fenêtre de gestion des insertions.

        Cette fenêtre permet d'afficher, modifier, supprimer ou ajouter des insertions
        à partir d'un gestionnaire XML. Elle est modale par rapport à la fenêtre parente.

        Args:
            parent (tk.Tk): Fenêtre principale parente.
            gestionnaire (GestionnaireInsertion): Gestionnaire contenant les insertions à afficher.
            termine (Callable | None): Fonction optionnelle à appeler à la fermeture de la fenêtre.
        """

        super().__init__(parent)  # Définir la fenêtre parent comme Toplevel
        self.fonction_termine = termine
        self.gestionnaire = gestionnaire
        self.title("Gérer les insertions automatiques")
        self.resizable(True, True)
        self.transient(parent)  # Faire en sorte que la fenêtre soit modale par rapport au parent
        self.grab_set()  # Empêcher les interactions avec la fenêtre parent tant que celle-ci est ouverte

        self.confirmation_en_cours = False  # Drapeau pour éviter les confirmations multiples

        # Frame pour la Listbox et la Scrollbar
        self.frame_liste = tk.Frame(self)
        self.frame_liste.pack(side="left", fill="y", padx=5, pady=5)

        # Liste des insertions
        self.liste_insertion = tk.Listbox(self.frame_liste, width=40)
        self.liste_insertion.pack(side="left", fill="y")

        # Scrollbar verticale pour la Listbox
        self.scrollbar_liste = tk.Scrollbar(self.frame_liste, orient="vertical")
        self.scrollbar_liste.pack(side="right", fill="y")

        # Lier la Listbox et la Scrollbar
        self.liste_insertion.config(yscrollcommand=self.scrollbar_liste.set)
        self.scrollbar_liste.config(command=self.liste_insertion.yview)

        self.remplir_liste_insertion()

        # Formulaires à droite
        self.frame_formulaire = tk.Frame(self)
        self.frame_formulaire.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        self.creer_ligne_champ("Nom *", 'nom')
        self.creer_ligne_champ("Description", 'description')
        self.creer_ligne_champ("Forme prononcée *", 'phrase')
        self.creer_ligne_contenu("Contenu *", 'contenu')

        self.bouton_appliquer = tk.Button(self.frame_formulaire,
                                          text="Appliquer",
                                          command=self.appliquer_modifications)
        self.bouton_appliquer.pack(side="left", padx=5, pady=5)
        self.bouton_appliquer.config(state="disabled")  # Désactiver par défaut

        self.modifications_en_cours = False

        self.bouton_nouveau = tk.Button(self.frame_formulaire,
                                        text="Nouvelle insertion",
                                        command=self.nouvelle_insertion)
        self.bouton_nouveau.pack(side="left", padx=5, pady=5)

        self.bouton_supprimer = tk.Button(self.frame_formulaire, text="Supprimer", command=self.supprimer_insertion)
        self.bouton_supprimer.pack(side="left", padx=5, pady=5)

        self.bouton_fermer = tk.Button(self.frame_formulaire, text="Fermer", command=self.fermer_fenetre)
        self.bouton_fermer.pack(side="right", padx=5, pady=5)

        self.entry_nom.config(state="disabled")
        self.entry_description.config(state="disabled")
        self.entry_phrase.config(state="disabled")
        self.text_contenu.config(state="disabled")

        self.entry_nom.bind("<KeyRelease>", self.on_field_change)
        self.entry_description.bind("<KeyRelease>", self.on_field_change)
        self.entry_phrase.bind("<KeyRelease>", self.on_field_change)
        self.text_contenu.bind("<KeyRelease>", self.on_field_change)

        self.selection_precedente = None  # stock la sélection précédente
        self.liste_insertion.bind("<<ListboxSelect>>", self.afficher_insertion)

        # Associer l'événement de fermeture à la méthode fermer_fenetre
        self.protocol("WM_DELETE_WINDOW", self.fermer_fenetre)  # Associer la fermeture de la fenêtre à la méthode

    def creer_ligne_champ(self, label_text: str, champ: str) -> None:
        """
        Crée un champ de saisie (Entry) avec son label associé dans le formulaire.

        Args:
            label_text (str): Texte affiché à gauche du champ.
            champ (str): Nom logique du champ (utilisé pour créer un attribut dynamique).
        """

        frame = tk.Frame(self.frame_formulaire)
        frame.pack(fill="x", padx=5, pady=5)

        label = tk.Label(frame, text=label_text)
        label.pack(side="left", padx=5, pady=5)

        entry = tk.Entry(frame)
        entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)

        setattr(self, f'entry_{champ}', entry)

    def creer_ligne_contenu(self, label_text: str, champ: str) -> None:
        """
        Crée un champ de texte multiligne (Text) avec son label associé.

        Args:
            label_text (str): Texte affiché à gauche.
            champ (str): Nom logique pour l'attribut Text.
        """

        frame = tk.Frame(self.frame_formulaire)
        frame.pack(fill="both", expand=True, padx=5, pady=5)

        label = tk.Label(frame, text=label_text)
        label.pack(side="left", padx=5, pady=5)

        petite_police = tkFont.Font(family="Helvetica", size=10)

        text = tk.Text(frame, height=10, font=petite_police)
        text.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        setattr(self, f'text_{champ}', text)

    def afficher_insertion(self, event: tk.Event) -> None:
        """
        Affiche les détails d'une insertion sélectionnée dans la Listbox.

        Args:
            event (tk.Event): Événement déclencheur (sélection).
        """
        # appelé par self.liste_insertion.bind("<<ListboxSelect>>", self.afficher_insertion)
        # Récupérer la nouvelle sélection
        selection = self.liste_insertion.curselection()

        if selection:
            new_selection = self.liste_insertion.get(selection)

            # Vérifier si la sélection a changé par rapport à la précédente
            if self.selection_precedente == new_selection:
                return  # Si la sélection est la même, ne rien faire

            # Mettre à jour la sélection précédente
            self.selection_precedente = new_selection

            if self.modifications_en_cours:
                reponse = messagebox.askyesno("Attention",
                                              "Vous avez des modifications non enregistrées. " +
                                              "Voulez-vous vraiment annuler ces modifications ?")
                if not reponse:
                    return

            name = self.liste_insertion.get(selection)

            # Rechercher l'insertion correspondant au nom
            full_key = next((key for key, value in self.gestionnaire.data.items() if value['name'] == name), None)

            if full_key:
                data = self.gestionnaire.data[full_key]

                # Réactiver les champs avant de remplir les valeurs
                self.activer_champs()

                self.entry_nom.delete(0, tk.END)
                self.entry_nom.insert(0, data['name'])

                self.entry_description.delete(0, tk.END)
                description = data.get('description', "")  # si il n'y a pas de description renvoi ""
                if description is None:
                    description = ''
                self.entry_description.insert(0, description)  # methode insert ne peut pas avoir None

                self.entry_phrase.delete(0, tk.END)
                self.entry_phrase.insert(0, full_key)

                self.text_contenu.delete("1.0", tk.END)
                self.text_contenu.insert(tk.END, data['body'])

                # Enregistrer la phrase actuelle avant modification
                self.old_phrase = full_key  # Sauvegarder la phrase d'origine

                # Désactiver le bouton Appliquer après avoir affiché l'insertion
                self.bouton_appliquer.config(state="disabled")
                self.modifications_en_cours = False
        else:
            self.selection_precedente = None

    def appliquer_modifications(self) -> None:
        """
        Applique les modifications faites à une insertion existante ou en ajoute une nouvelle.
        Met à jour le dictionnaire et sauvegarde dans le fichier XML.
        """

        time.sleep(0.1)
        nom = self.entry_nom.get().strip()
        description = self.entry_description.get().strip()
        phrase = self.entry_phrase.get().strip()
        contenu = self.text_contenu.get("1.0", tk.END).strip()

        if not nom or not phrase or not contenu:
            messagebox.showwarning("Erreur",
                                   "Le nom, la forme prononcée et le contenu sont requis " +
                                   "pour ajouter une nouvelle insertion.")
            return

        # Supposons que self.old_phrase contienne la phrase originale (avant modification)
        if self.old_phrase in self.gestionnaire.data:
            if phrase != self.old_phrase:
                # Si la phrase a changé, il faut supprimer l'ancienne entrée et ajouter la nouvelle
                del self.gestionnaire.data[self.old_phrase]
                self.gestionnaire.data[phrase] = {'name': nom, 'description': description, 'body': contenu}
                messagebox.showinfo("Info", "Phrase modifiée et insertion mise à jour !")
            else:
                # Si la phrase n'a pas changé, on met juste à jour les autres champs
                self.gestionnaire.data[phrase]['name'] = nom
                self.gestionnaire.data[phrase]['description'] = description
                self.gestionnaire.data[phrase]['body'] = contenu
                messagebox.showinfo("Info", "Modifications appliquées !")

        else:
            # Nouvelle insertion
            self.gestionnaire.ajouter_insertion(nom, description, phrase, contenu)
            messagebox.showinfo("Info", "Nouvelle insertion ajoutée !")

        # Sauvegarder après modification ou ajout
        self.gestionnaire.sauvegarder_modifications()

        # Recréer la liste d'insertions dans la Listbox
        self.remplir_liste_insertion()

        # Désactiver les champs et le bouton Appliquer après l'application
        self.modifications_en_cours = False
        self.bouton_appliquer.config(state="disabled")
        self.bouton_nouveau.config(state='normal')
        self.desactiver_champs()

    def remplir_liste_insertion(self) -> None:
        """
        Vide et remplit la Listbox avec les noms triés des insertions disponibles.
        """

        # Vider la Listbox
        self.liste_insertion.delete(0, tk.END)

        # Trier les noms des insertions par ordre alphabétique
        noms = sorted(self.gestionnaire.data.items(), key=lambda item: item[1]['name'])

        # Réinsérer les éléments triés
        for _, insertion in noms:
            self.liste_insertion.insert(tk.END, insertion['name'])

    def supprimer_insertion(self) -> None:
        """
        Supprime l'insertion actuellement sélectionnée après confirmation.
        Met à jour l'affichage et sauvegarde les modifications.
        """

        selection = self.liste_insertion.curselection()
        if selection:
            if messagebox.askyesno("Confirmation", "Voulez-vous vraiment supprimer cette insertion ?"):
                # Récupérer le nom sélectionné
                name = self.liste_insertion.get(selection)

                # Rechercher la clé complète correspondant à ce nom dans self.gestionnaire.data
                full_key = next((key for key, value in self.gestionnaire.data.items() if value['name'] == name), None)

                if full_key:
                    # Supprimer l'insertion de self.gestionnaire.data
                    del self.gestionnaire.data[full_key]

                    # Supprimer l'insertion de la Listbox
                    self.liste_insertion.delete(selection)

                    # Vider les champs après suppression
                    self.vider_champs()

                    # Sauvegarder après la suppression
                    self.gestionnaire.sauvegarder_modifications()

                    # Message de succès
                    messagebox.showinfo("Info", "Insertion supprimée avec succès.")
                else:
                    messagebox.showwarning("Erreur", "Insertion non trouvée.")
        else:
            messagebox.showwarning("Erreur", "Aucune insertion sélectionnée à supprimer.")

    def nouvelle_insertion(self) -> None:
        """
        Vide les champs du formulaire pour permettre la création d'une nouvelle insertion.
        """

        self.entry_nom.delete(0, tk.END)
        self.entry_description.delete(0, tk.END)
        self.entry_phrase.delete(0, tk.END)
        self.text_contenu.delete("1.0", tk.END)

        # Activer les champs pour permettre la saisie
        self.activer_champs()

        self.modifications_en_cours = True
        self.bouton_appliquer.config(state="normal")  # Activer le bouton Appliquer pour une nouvelle insertion
        self.bouton_nouveau.config(state='disable')
        self.old_phrase = None

    def on_field_change(self, event: tk.Event) -> None:
        """
        Active le bouton 'Appliquer' lorsqu'un champ est modifié.

        Args:
            event (tk.Event): L'événement déclenché lors de la modification.
        """

        # Activer le bouton "Appliquer" quand un champ est modifié
        self.modifications_en_cours = True
        self.bouton_appliquer.config(state="normal")
        self.bouton_nouveau.config(state='disable')

    def fermer_fenetre(self) -> None:
        """
        Ferme la fenêtre après confirmation si des modifications non enregistrées sont détectées.
        """

        # Empêcher la fermeture multiple ou la confirmation multiple
        if self.confirmation_en_cours:
            return
        if self.modifications_en_cours:
            self.confirmation_en_cours = True  # Activer le drapeau
            reponse = messagebox.askyesno("Attention",
                                          "Vous avez des modifications non enregistrées. " +
                                          "Voulez-vous vraiment quitter sans enregistrer ?")
            self.confirmation_en_cours = False  # Désactiver le drapeau après réponse
            if not reponse:
                return  # Annuler la fermeture
        self.fonction_termine()  # Appel à la méthode pour terminer

    def activer_champs(self) -> None:
        """Active tous les champs de saisie de l'interface."""

        self.entry_nom.config(state="normal")
        self.entry_description.config(state="normal")
        self.entry_phrase.config(state="normal")
        self.text_contenu.config(state="normal")

    def desactiver_champs(self) -> None:
        """Désactive tous les champs de saisie pour éviter les modifications involontaires."""

        self.entry_nom.config(state="disabled")
        self.entry_description.config(state="disabled")
        self.entry_phrase.config(state="disabled")
        self.text_contenu.config(state="disabled")

    def vider_champs(self) -> None:
        """Efface tous les champs de saisie et désactive l’interface de modification."""

        self.entry_nom.delete(0, tk.END)
        self.entry_description.delete(0, tk.END)
        self.entry_phrase.delete(0, tk.END)
        self.text_contenu.delete("1.0", tk.END)
        self.desactiver_champs()  # Désactiver les champs après avoir vidé leur contenu


if __name__ == "__main__":
    """
    Point d'entrée de test pour la fenêtre `FenetreGestion`.

    Ce bloc permet de lancer la fenêtre de gestion des insertions de manière autonome,
    sans démarrer toute l'application RecoVocale. Utile pour tester l'interface ou la gestion XML.
    """

    root = tk.Tk()
    root.title("Test FenetreGestion")

    fichier_xml = "config/insertions.xml"

    try:
        # Initialisez la classe avec le fichier XML
        gestionnaire = GestionnaireInsertion(fichier_xml)

        # Initialisez et affichez la FenetreGestion pour test
        fenetre_gestion = FenetreGestion(root, gestionnaire)
        # fenetre_gestion.pack()  # Ajoutez la fenêtre à la fenêtre Tkinter

    except Exception as e:
        print(f"Erreur lors de l'initialisation du gestionnaire ou de la FenetreGestion : {e}")

    # Lancez la boucle principale Tkinter
    root.mainloop()
