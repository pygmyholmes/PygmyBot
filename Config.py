import configparser
import os.path

class Config:

    path: str = "config\config.ini"

    CONFIG = configparser.ConfigParser()
    CONFIG.read(os.path.join(os.path.dirname(__file__), path))