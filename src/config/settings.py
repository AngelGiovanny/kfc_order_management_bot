import os
from dataclasses import dataclass
from typing import List


@dataclass
class DatabaseConfig:
    user: str = os.getenv('DB_USER', 'sis_tercernivel')
    password: str = os.getenv('DB_PASSWORD', 'T3rc3rn1*m4x')
    driver: str = os.getenv('DB_DRIVER', 'ODBC Driver 17 for SQL Server')
    timeout: int = int(os.getenv('DB_TIMEOUT', '15'))  # Reducido a 15s


@dataclass
class BotConfig:
    token: str = os.getenv('BOT_TOKEN', '7384588957:AAFWIsWQTyoNdK9Fa18HaneW4wsGqdyjRlM')
    admins: List[int] = None
    authorized_group_id: int = int(os.getenv('AUTHORIZED_GROUP_ID', '-1002147164153'))
    max_inactivity_time: int = int(os.getenv('MAX_INACTIVITY_TIME', '120'))  # Aumentado a 2min

    def __post_init__(self):
        if self.admins is None:
            self.admins = [5983589008, 1474400044, 5387458972, 6364928336,
                           7365984572, 8195561177, 7534604655, 6467565615]


@dataclass
class LogConfig:
    base_dir: str = os.getenv('LOG_DIR', 'C:/ChatBot/Logs')
    reprints_dir: str = os.getenv('REPRINTS_DIR', 'C:/ChatBot/Impresiones')
    log_level: str = os.getenv('LOG_LEVEL', 'INFO')
    max_file_size: int = int(os.getenv('MAX_FILE_SIZE', '10485760'))  # 10MB
    backup_count: int = int(os.getenv('BACKUP_COUNT', '5'))


@dataclass
class PrintConfig:
    base_url: str = os.getenv('PRINT_BASE_URL', 'http://{server_name}:880')
    api_url: str = os.getenv('PRINT_API_URL', 'http://192.168.101.96:5000/api/ImpresionTickets/Impresion')
    max_reprints: dict = None

    def __post_init__(self):
        if self.max_reprints is None:
            self.max_reprints = {
                'factura': 1,
                'nota_credito': 1,
                'comanda': 2
            }


@dataclass
class ServerConfig:
    # Configuración de servidores por rango de tiendas
    server_mapping = {
        'K1': '192.168.101.27',  # K100, K101, etc. - Servidor de pruebas
        'default': '10.101.{store_num}.20'  # Para otras tiendas
    }


class Settings:
    def __init__(self):
        self.database = DatabaseConfig()
        self.bot = BotConfig()
        self.logging = LogConfig()
        self.print = PrintConfig()
        self.server = ServerConfig()


settings = Settings()