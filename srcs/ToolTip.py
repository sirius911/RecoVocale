import tkinter as tk

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None

        # Lier les événements Enter et Leave pour afficher et cacher la tooltip
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        if self.tooltip_window or not self.text:
            return

        # Créer une nouvelle fenêtre pour la tooltip
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25

        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        tw.attributes("-topmost", True)

        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

# Exemple d'utilisation avec un bouton
# root = tk.Tk()

# # Image fictive pour l'exemple
# record_image = tk.PhotoImage(width=50, height=50)  # Utilisez votre propre image

# # Création d'un cadre pour les boutons
# button_frame = tk.Frame(root)
# button_frame.pack(pady=20)

# # Bouton avec une image
# rec_button = tk.Button(button_frame, image=record_image, command=lambda: print("Recording..."))
# rec_button.pack(side=tk.LEFT, padx=10)

# # Ajouter une bulle d'information (tooltip) au bouton
# ToolTip(rec_button, "Démarrer/Arrêter l'enregistrement")

# root.mainloop()
