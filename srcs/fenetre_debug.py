import sys
import tkinter as tk
from tkinter import scrolledtext


class RedirectOutput:
    def __init__(self, text_widget):
        """Initialise la redirection des sorties vers un widget Tkinter."""
        self.text_widget = text_widget

    def write(self, message):
        """Écrit le message dans la zone de texte du widget Tkinter, si celui-ci existe."""
        if self.text_widget.winfo_exists():
            self.text_widget.insert(tk.END, message)
            self.text_widget.see(tk.END)  # Fait défiler vers le bas automatiquement
        else:
            # Le widget n'existe plus, ignorer les messages
            pass

    def flush(self):
        """Flush requis pour la compatibilité avec certains systèmes."""
        pass


class DebugWindow:
    def __init__(self, root):
        # Création de la fenêtre fille
        self.debug_window = tk.Toplevel(root)
        self.debug_window.title("Fenêtre de débogage")
        self.debug_window.geometry("415x390")  # Dimensions de la fenêtre fille
        self.debug_window.protocol("WM_DELETE_WINDOW", self.on_debug_close)
        self.taille_font_status = 8
        self.taille_font_log = 8

        # Ajouter une zone de texte défilante pour afficher les logs
        self.log_area = scrolledtext.ScrolledText(self.debug_window,
                                                  height=10, bg='black',
                                                  fg="white", font=("Courier", self.taille_font_log))
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=5)

        # Ajouter une zone de texte pour afficher les statuts mis à jour régulièrement
        self.status_area = tk.Text(self.debug_window, height=6, bg="light grey")
        self.status_area.pack(fill=tk.BOTH, expand=True)

        # Sauvegarde des stdout et stderr originaux
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

        # Rediriger les sorties `print` vers la zone `log_area` seulement si compilé
        if getattr(sys, 'frozen', False):
            sys.stdout = RedirectOutput(self.log_area)
            sys.stderr = RedirectOutput(self.log_area)  # Redirige aussi les erreurs

    def log_message(self, message):
        """Ajoute un message personnalisé à la zone de logs."""
        self.log_area.insert(tk.END, message + '\n')
        self.log_area.see(tk.END)  # Faire défiler automatiquement vers le bas

    def get_log_message(self):
        try:
            if self.log_area:
                return self.log_area.get('1.0', tk.END)
            return ""
        except tk.TclError:
            return "[log perdu : log_area détruit]"

    def update_status(self, status):
        """Met à jour les statuts dans la zone de statut."""
        if self.status_area.winfo_exists():
            self.status_area.delete('1.0', tk.END)  # Effacer le statut précédent
            self.status_area.insert(tk.END, status)

    def on_debug_close(self):
        """Gestion de la fermeture de la fenêtre fille."""
        self.debug_window.withdraw()  # Masquer la fenêtre au lieu de la fermer
        # Restaurer les stdout et stderr originaux
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr

    def append_status_with_format(self, message, color="black", font_style="normal"):
        """Ajoute du texte à la zone de statut avec une couleur et un style de police."""
        if self.status_area.winfo_exists():
            # Configurer le style du texte
            if font_style == "italic":
                self.status_area.tag_configure(f"formatted_{font_style}",
                                               font=("Helvetica",
                                                     self.taille_font_status,
                                                     "italic"))
            elif font_style == "bold":
                self.status_area.tag_configure(f"formatted_{font_style}",
                                               font=("Helvetica",
                                                     self.taille_font_status,
                                                     "bold"))
            else:
                self.status_area.tag_configure(f"formatted_{font_style}",
                                               font=("Helvetica",
                                                     self.taille_font_status,
                                                     "normal"))

            # Configurer la couleur du texte
            self.status_area.tag_configure(f"colored_{color}", foreground=color)

            # Insérer le nouveau texte sans effacer ce qui est déjà là
            self.status_area.insert(tk.END, message, (f"formatted_{font_style}", f"colored_{color}"))
            self.status_area.see(tk.END)  # Faire défiler vers le bas automatiquement

    def delete_status(self):
        if self.status_area.winfo_exists():
            self.status_area.delete('1.0', tk.END)


# Test rapide pour voir la fenêtre en fonctionnement
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Fenêtre principale")
    root.geometry("200x150")

    debug_win = DebugWindow(root)

    # Ajout de quelques messages de test
    debug_win.log_message("Débogage activé")
    debug_win.update_status("Statut : OK")

    # Ajout d'un bouton pour afficher/masquer la fenêtre de débogage
    def toggle_debug_window():
        if not debug_win.debug_window.winfo_viewable():
            debug_win.debug_window.deiconify()  # Afficher la fenêtre de débogage
        else:
            debug_win.debug_window.withdraw()  # Masquer la fenêtre de débogage

    # Bouton dans la fenêtre principale pour ouvrir/fermer la fenêtre de débogage
    toggle_button = tk.Button(root, text="Afficher/Masquer Débogage", command=toggle_debug_window)
    toggle_button.pack(pady=20)

    root.mainloop()
