# import pystray
# from pystray import MenuItem as item
from utils_socket import check_server_status
from info import *
from Transcription import Transcription
import tkinter as tk

class Mode:
    def __init__(self, app):
        self.app = app
        self.root = app.root
        self.mod_var = tk.StringVar()
        self.transcription = Transcription()
        self.enter()

    def enter(self):
        self.root.resizable(self.mode.resizable, self.mode.resizable)
        self.root.attributes("-topmost", self.mode.topmost)
        self.root.geometry(f"{self.mode.window_width}x{self.mode.window_height}+{self.app.config.x_window}+{self.app.config.y_window}")
        # self.create_systray_icon()

    def show_window(self, icon, item):
        # self.simulate_keyboard_var.set(False)
        self.root.deiconify()
        self.is_hidden = False

    # def update_status(self):
    #     self.update_icon()
    #     self.update_icon_image(self.create_error_image())

    def update_transcription(self, transcriptions):
        pass

    def get_selected_text(self):
        return self.transcription.get()
    
    # def start_client(self):
    #     pass
    
    def stop_client(self):
        pass

    def copy_to_clipboard(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.transcription.get())

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

    def update(self):
        self._update_rec_circle()
        self._update_image_button()

    def info(self):
        #print info TODO: A mettre en fênetre
        print('--------------------------------------------------------------------')
        print(f"Version : v{VERSION}")
        if check_server_status(self.app.config.server_ip, self.app.config.port):
            _serv = f"Connected @{self.app.config.server_ip}:{self.app.config.port}"
        else:
            _serv = f"Not Connected @{self.app.config.server_ip}:{self.app.config.port}"
        print(f"Model = {self.client_manager.client.get_model_path()}")
        print(f"Serveur : {_serv}")
        print(f"Micro : {self.app.mic.micro_name if self.app.mic else None}")
        print(f"Mode = {self.name()} - Simulation Clavier: {self.app.simulate_keyboard}")
        print(f"Raccourci : {self.app.keyboard_shortcut}")
        print(f"Debug : {self.app.config.debug}")
        print(f"Position actuelle de la fenêtre : x={self.app.root.winfo_x()}, y={self.app.root.winfo_y()}")
        print('--------------------------------------------------------------------')

    def name(self):
        return self.mode.name
    
    def toggle_start_stop(self):
        """
        Toggle the start/stop state of the transcription client.
        """
        # print(f"mode = {self.name()}")
        if self.app.recording:
            self.pause()
        else:
            self.unpause()

    def exit(self):
        for widget in self.root.winfo_children():
            widget.destroy()
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