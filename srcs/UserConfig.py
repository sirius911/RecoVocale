import os
import configparser

class UserConfig:
    def __init__(self):
        # Définir le chemin du répertoire de configuration dans %APPDATA%\RecoVocale
        self.config_dir = os.path.join(os.getenv('APPDATA'), 'RecoVocale')
        self.config_file = os.path.join(self.config_dir, "user_config.ini")
        print(f"init avec {self.config_file}")
        # Valeurs par défaut
        self._server_ip = "10.1.147.12"
        self._port = "30000"
        self._shortcut = "F3"
        self._mode = "SMALL"
        self.x_window = "10"
        self.y_window = "10"
        self.debug = False
        # Lire la configuration si le fichier existe, sinon la créer
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
        self.x_window = config.get('SETTINGS', 'X_WINDOW', fallback=self.x_window)
        self.y_window = config.get('SETTINGS', 'Y_WINDOW', fallback=self.y_window)
        self.debug = (config.get('SETTINGS', 'DEBUG', fallback=self.debug) == True)
        
    def save_config(self, root):
        """Sauvegarde la configuration dans un fichier."""
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
        
        config = configparser.ConfigParser()
        config['SETTINGS'] = {
            'SERVEUR_IP': self._server_ip,
            'PORT': self._port,
            'SHORTCUT': self._shortcut,
            'MODE': self._mode,
            'X_WINDOW': root.winfo_x(),
            'Y_WINDOW': root.winfo_y(),
            'DEBUG': self.debug
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

    @property
    def port(self):
        return self._port
    
    @port.setter
    def port(self, value):
        self._port = value
    
    @property
    def shortcut(self):
        return self._shortcut
    
    @shortcut.setter
    def shortcut(self, value):
        self._shortcut = value
    
    @property
    def mode(self):
        return self._mode
    
    @mode.setter
    def mode(self, value):
        self._mode = value
