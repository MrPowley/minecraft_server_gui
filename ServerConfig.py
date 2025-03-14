import os
import sys
import yaml


class ServerConfig:
    """Gère la configuration du serveur Minecraft."""

    DEFAULT_CONFIG = {
        "server-name": "",
        "java_path": "java",
        "server_path": "",
        "server_jar": "paper.jar",
        "ram": 4096,
        "log-exclusion": {
            "absolute": [],
            "regex": []
        },
        "interface-theme": "light",
        "font" : "consolas",

    }

    def __init__(self, config_path="config.yml"):
        """Initialise la configuration en chargeant le fichier ou en créant un fichier par défaut."""
        self.pwd = os.path.dirname(os.path.abspath(sys.argv[0]))
        self.config_path = os.path.join(self.pwd, config_path)
        self.config = self.load_config()

    def load_config(self):
        """Charge la configuration depuis un fichier YAML, sinon utilise la configuration par défaut."""
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as file:
                return yaml.safe_load(file) or self.DEFAULT_CONFIG
        else:
            self.save_config(self.DEFAULT_CONFIG)
            return self.DEFAULT_CONFIG

    def save_config(self, config=None):
        """Enregistre la configuration actuelle dans le fichier YAML."""
        if config is None:
            config = self.config
        with open(self.config_path, 'w', encoding="utf-8") as file:
            yaml.dump(config, file, default_flow_style=False)

    def get(self, key, default=None):
        """Récupère une valeur de la configuration avec une valeur par défaut."""
        return self.config.get(key, default)

    def set(self, key, value):
        """Met à jour une valeur dans la configuration et sauvegarde les changements."""
        self.config[key] = value
        self.save_config()

    def get_log_exceptions_absolute(self):
        """Récupère les valeurs des exclusions absolues"""
        return self.get("log-exclusion")["absolute"]

    def get_log_exceptions_regex(self):
        """Récupère les valeurs des exclusions regex"""
        return self.get("log-exclusion")["regex"]
