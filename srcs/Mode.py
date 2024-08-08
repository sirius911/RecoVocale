# import pystray
# from pystray import MenuItem as item

class Mode:
    def __init__(self, app):
        self.app = app
        self.root = app.root
        # self.root.resizable(False, False)
        self.enter()

    def enter(self):
        pass
        # self.create_systray_icon()

    # def exit(self):
    #      # pour le switch mode
    #     pass

    

    def show_window(self, icon, item):
        self.simulate_keyboard_var.set(False)
        self.root.deiconify()
        self.is_hidden = False

    # def update_status(self):
    #     self.update_icon()
    #     self.update_icon_image(self.create_error_image())

    # def update_transcription(self, transcriptions):
    #     return transcriptions

    def hide_window(self):
        self.simulate_keyboard_var.set(True)
        self.is_hidden = True
    
    def exit_app(self):
        # self.icon.stop()
        self.app.on_closing()

    def _update_rec_circle(self):
        fill = 'red' if self.app.recording else 'grey'
        self.rec_canvas.itemconfig(self.rec_circle, fill=fill)

    def _update_image_button(self):
        if self.app.recording:
            self.rec_button.config(image=self.record_image)
        else:
            self.rec_button.config(image=self.pause_image)

    def _toggle_record(self):
        if self.app.recording:
            self.app.pause()  # Call pause function
        else:
            self.app.unpause()  # Call unpause function

    def update(self):
        self._update_rec_circle()
        self._update_image_button()
    # def load_and_resize_image(self, path, size):
    #     image = Image.open(path)
    #     image = image.resize(size, Image.LANCZOS)  # Use LANCZOS for high-quality downsizing
    #     return ImageTk.PhotoImage(image)

#-----------------------------------------------------------------------
#                                  MODE SYSTRAY
#-----------------------------------------------------------------------
    # def create_systray_icon(self):
    #     self.icon = pystray.Icon("RecoVocale")
    #     self.icon.icon = self.create_image(50)
    #     self.icon.menu = pystray.Menu(
    #         item('Show', self.show_window),
    #         # item('Raccourci Clavier', self.app.change_shortcut),
    #         item('Exit', self.exit_app)
    #     )
    #     self.icon.run_detached()
    #     self.update_icon()

    # def update_icon(self):
    #     status_serveur = 'Connected' if self.app.status_server else 'Not connected'
    #     text = f"RecoVocale (v{VERSION})[{self.app.keyboard_shortcut}] {status_serveur}"
    #     self.icon.title = text
    #     if not self.app.status_server:
    #         self.update_icon_image(self.create_error_image())

    # def create_image(self, niveau:int):
    #     """
    #     Creates a 64x64 image with a rectangle of specified color and height.

    #     Parameters:
    #     self (object): A reference to the instance of the class.
    #     niveau (int): The height of the rectangle as a percentage of 64 pixels.
    #     record (int): True if the client is recording 
    #     Returns:
    #     Image: The generated image with the colored rectangle.
    #     """
    #     # Create a 64x64 pixel image with a white background
    #     img = Image.new('RGB', (64, 64), "white")
    #     draw = ImageDraw.Draw(img)
    #     if self.app.running():
    #         # Dessiner un cercle rouge au centre
    #         draw.ellipse((16, 16, 50, 50), fill="red")
    #     else:
    #         # Calculate the height of the rectangle to be drawn
    #         height = int(niveau / 2000 * 64)

    #         # Draw the rectangle with the specified color
    #         draw.rectangle([0, 64 - height, 64, 64], fill="blue")

    #     return img
    
    # def create_error_image(self):
    #     # Create a 64x64 pixel image with a white background
    #     img = Image.new('RGB', (64, 64), "white")
    #     draw = ImageDraw.Draw(img)

    #     # Draw the first diagonal line from top-left to bottom-right
    #     draw.line((0, 0, 64, 64), fill="red", width=10)

    #     # Draw the second diagonal line from top-right to bottom-left
    #     draw.line((64, 0, 0, 64), fill="red", width=10)

    #     return img
    
    # def update_icon_image(self, image):
    #     self.icon.icon = image