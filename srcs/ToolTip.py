import tkinter as tk


class ToolTip:
    """
    Gère l'affichage d'une infobulle (tooltip) pour un widget Tkinter.

    Affiche automatiquement un petit encart d'aide lorsqu'on survole le widget
    avec la souris, et le masque lorsqu'on en sort.
    """

    def __init__(self, widget: tk.Widget, text: str):
        """
        Initialise l'infobulle pour un widget donné.

        Args:
            widget (tk.Widget): Le widget Tkinter auquel attacher l'infobulle.
            text (str): Le texte à afficher dans l'infobulle.
        """
        self.widget = widget
        self.text = text
        self.tooltip_window = None

        # Lier les événements Enter et Leave pour afficher et cacher la tooltip
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None) -> None:
        """
        Affiche l'infobulle à proximité du curseur si elle n'est pas déjà visible.
        """

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

    def hide_tooltip(self, event=None) -> None:
        """
        Masque et détruit l'infobulle si elle est visible.
        """

        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None
