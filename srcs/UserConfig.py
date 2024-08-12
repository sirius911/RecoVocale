import os
import configparser

class UserConfig:
    def __init__(self):
        self.config_dir = "config"
        self.config_file = os.path.join(self.config_dir, "user_config.ini")
        
        # Valeurs par défaut
        self._server_ip = "10.1.11.215"
        self._port = "9090"
        self._shortcut = "F3"
        self._mode = "SMALL"
        self._x_window = "10"
        self._y_window = "10"
        
        # Lire la configuration si le fichier existe
        if os.path.exists(self.config_file):
            self.load_config()
        else:
            self.save_config()

    def load_config(self):
        """Charge la configuration depuis le fichier."""
        config = configparser.ConfigParser()
        config.read(self.config_file)
        
        self._server_ip = config.get('SETTINGS', 'SERVEUR_IP', fallback=self._server_ip)
        self._port = config.get('SETTINGS', 'PORT', fallback=self._port)
        self._shortcut = config.get('SETTINGS', 'SHORTCUT', fallback=self._shortcut)
        self._mode = config.get('SETTINGS', 'MODE', fallback=self._mode)
        self._x_window = config.get('SETTINGS', 'X_WINDOW', fallback=self._x_window)
        self._y_window = config.get('SETTINGS', 'Y_WINDOW', fallback=self._y_window)

    def save_config(self):
        """Sauvegarde la configuration dans un fichier."""
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
        
        config = configparser.ConfigParser()
        config['SETTINGS'] = {
            'SERVEUR_IP': self._server_ip,
            'PORT': self._port,
            'SHORTCUT': self._shortcut,
            'MODE': self._mode,
            'X_WINDOW': self._x_window,
            'Y_WINDOW': self._y_window
        }
        print(f"Sauvegarde {self.config_file} ...", end =' ')
        with open(self.config_file, 'w') as configfile:
            config.write(configfile)
        print("Ok")
        
    # Getters et Setters
    @property
    def server_ip(self):
        return self._server_ip
    
    @server_ip.setter
    def server_ip(self, value):
        self._server_ip = value
        self.save_config()

    @property
    def port(self):
        return self._port
    
    @port.setter
    def port(self, value):
        self._port = value
        self.save_config()
    
    @property
    def shortcut(self):
        return self._shortcut
    
    @shortcut.setter
    def shortcut(self, value):
        self._shortcut = value
        self.save_config()
    
    @property
    def mode(self):
        return self._mode
    
    @mode.setter
    def mode(self, value):
        self._mode = value
        self.save_config()

    @property
    def x_window(self):
        return self._x_window
    
    @x_window.setter
    def x_window(self, value):
        self._x_window = value
        self.save_config()
    
    @property
    def y_window(self):
        return self._y_window

    @y_window.setter
    def y_window(self, value):
        self._y_window = value
        self.save_config()

# Exemple d'utilisation
# if __name__ == "__main__":
#     config = UserConfig()
#     print(config.server_ip)
#     config.server_ip = "192.168.0.1"
#     print(config.server_ip)
