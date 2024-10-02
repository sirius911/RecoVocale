import tkinter as tk
from tkinter import messagebox
import tkinter.font as tkFont  # Importer le module pour gérer la police
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom


class GestionnaireInsertion:
    def __init__(self, fichier_xml):
        self.fichier_xml = fichier_xml
        self.data = self.charger_donnees()

    def charger_donnees(self):
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

    def get(self):
        # Créer un dictionnaire avec la clé étant la spoken_phrase sans le mot "insérer"
        return {key.replace('insérer ', ''): value['body'] for key, value in self.data.items()}


    def ajouter_insertion(self, name, description, spoken_phrase, body):
        if spoken_phrase not in self.data:
            self.data[spoken_phrase] = {'name': name, 'description': description, 'body': body}

    def sauvegarder_modifications(self):
        root = ET.Element("SpeechAutoTexts", xmlns="http://nuance.com/NAS/AutoTextImport")
        
        for spoken_phrase, data in self.data.items():
            auto_text = ET.SubElement(root, "SpeechAutoText")

            # Ajouter les éléments au XML
            ET.SubElement(auto_text, "Format").text = "1"
            ET.SubElement(auto_text, "Name").text = data['name']
            ET.SubElement(auto_text, "Description").text = data.get('description', "")  # Description vide si None
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
    def __init__(self, parent, gestionnaire):
        super().__init__(parent)  # Définir la fenêtre parent comme Toplevel
        self.gestionnaire = gestionnaire
        self.title("Gérer les insertions automatiques")
        self.resizable(True, True)
        self.transient(parent)  # Faire en sorte que la fenêtre soit modale par rapport au parent
        self.grab_set()  # Empêcher les interactions avec la fenêtre parent tant que celle-ci est ouverte

        # Liste des insertions
        self.liste_insertion = tk.Listbox(self, width=30)
        self.liste_insertion.pack(side="left", fill="y", padx=5, pady=5)

        # Trier et insérer les noms dans la Listbox
        noms = sorted(self.gestionnaire.data.items(), key=lambda item: item[1]['name'])
        for _, insertion in noms:
            self.liste_insertion.insert(tk.END, insertion['name'])

        # Formulaires à droite
        self.frame_formulaire = tk.Frame(self)
        self.frame_formulaire.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        self.creer_ligne_champ("Nom *", 'nom')
        self.creer_ligne_champ("Description", 'description')
        self.creer_ligne_champ("Forme prononcée *", 'phrase')
        self.creer_ligne_contenu("Contenu *", 'contenu')

        self.bouton_appliquer = tk.Button(self.frame_formulaire, text="Appliquer", command=self.appliquer_modifications)
        self.bouton_appliquer.pack(side="left", padx=5, pady=5)

        self.bouton_nouveau = tk.Button(self.frame_formulaire, text="Nouvelle insertion", command=self.nouvelle_insertion)
        self.bouton_nouveau.pack(side="left", padx=5, pady=5)

        self.bouton_supprimer = tk.Button(self.frame_formulaire, text="Supprimer", command=self.supprimer_insertion)
        self.bouton_supprimer.pack(side="left", padx=5, pady=5)

        self.bouton_fermer = tk.Button(self.frame_formulaire, text="Fermer", command=self.destroy)
        self.bouton_fermer.pack(side="right", padx=5, pady=5)

        self.liste_insertion.bind("<<ListboxSelect>>", self.afficher_insertion)


    def creer_ligne_champ(self, label_text, champ):
        """Crée une ligne avec un label et un champ Entry."""
        frame = tk.Frame(self.frame_formulaire)
        frame.pack(fill="x", padx=5, pady=5)

        label = tk.Label(frame, text=label_text)
        label.pack(side="left", padx=5, pady=5)

        entry = tk.Entry(frame)
        entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)

        setattr(self, f'entry_{champ}', entry)

    def creer_ligne_contenu(self, label_text, champ):
        """Crée une ligne avec un label et un champ Text."""
        frame = tk.Frame(self.frame_formulaire)
        frame.pack(fill="both", expand=True, padx=5, pady=5)

        label = tk.Label(frame, text=label_text)
        label.pack(side="left", padx=5, pady=5)

        petite_police = tkFont.Font(family="Helvetica", size=10)

        text = tk.Text(frame, height=10, font=petite_police)
        text.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        setattr(self, f'text_{champ}', text)

    def afficher_insertion(self, event):
        selection = self.liste_insertion.curselection()
        if selection:
            name = self.liste_insertion.get(selection)

            # Rechercher l'insertion correspondant au nom
            full_key = next((key for key, value in self.gestionnaire.data.items() if value['name'] == name), None)

            if full_key:
                data = self.gestionnaire.data[full_key]

                self.entry_nom.delete(0, tk.END)
                self.entry_nom.insert(0, data['name'])

                self.entry_description.delete(0, tk.END)
                self.entry_description.insert(0, data['description'])

                self.entry_phrase.delete(0, tk.END)
                self.entry_phrase.insert(0, full_key)

                self.text_contenu.delete("1.0", tk.END)
                self.text_contenu.insert(tk.END, data['body'])
    def appliquer_modifications(self):
        phrase = self.entry_phrase.get()
        if phrase in self.gestionnaire.data:
            self.gestionnaire.data[phrase]['name'] = self.entry_nom.get()
            self.gestionnaire.data[phrase]['description'] = self.entry_description.get()
            self.gestionnaire.data[phrase]['body'] = self.text_contenu.get("1.0", tk.END).strip()
            messagebox.showinfo("Info", "Modifications appliquées !")
        else:
            self.gestionnaire.ajouter_insertion(
                self.entry_nom.get(),
                self.entry_description.get(),
                self.entry_phrase.get(),
                self.text_contenu.get("1.0", tk.END).strip()
            )
            self.liste_insertion.insert(tk.END, phrase)
            messagebox.showinfo("Info", "Nouvelle insertion ajoutée !")
        
        # Sauvegarder après modification ou ajout
        self.gestionnaire.sauvegarder_modifications()


    def supprimer_insertion(self):
        """Supprime l'insertion sélectionnée."""
        selection = self.liste_insertion.curselection()
        if selection:
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
                self.nouvelle_insertion()

                # Message de succès
                messagebox.showinfo("Info", "Insertion supprimée avec succès.")
            else:
                messagebox.showwarning("Erreur", "Insertion non trouvée.")
        else:
            messagebox.showwarning("Erreur", "Aucune insertion sélectionnée à supprimer.")


    def nouvelle_insertion(self):
        """Vide tous les champs pour ajouter une nouvelle insertion."""
        self.entry_nom.delete(0, tk.END)
        self.entry_description.delete(0, tk.END)
        self.entry_phrase.delete(0, tk.END)
        self.text_contenu.delete("1.0", tk.END)


if __name__ == "__main__":
    gestionnaire = GestionnaireInsertion("config/insertions.xml")
    app = FenetreGestion(gestionnaire)
    app.mainloop()
