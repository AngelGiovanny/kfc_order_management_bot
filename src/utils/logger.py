import logging
import os
from datetime import datetime
from pathlib import Path

from src.config.settings import settings


class StructuredLogger:
    def __init__(self):
        self.settings = settings.logging
        self._ensure_directories()
        self._setup_loggers()

    def _ensure_directories(self):
        """Create necessary directories for logging"""
        try:
            base_dir = Path(self.settings.base_dir)
            connections_dir = base_dir / "connections"

            # Create main directories
            base_dir.mkdir(parents=True, exist_ok=True)
            connections_dir.mkdir(parents=True, exist_ok=True)

            print(f"✅ Directorios de log creados en: {base_dir}")

        except Exception as e:
            print(f"⚠️ Error creando directorios de log: {e}")
            # Fallback a directorio temporal
            self.settings.base_dir = "/tmp/kfc_bot_logs"
            Path(self.settings.base_dir).mkdir(parents=True, exist_ok=True)

    def _get_log_path(self, log_type: str, prefix: str = "") -> Path:
        """Get log file path with date structure"""
        today = datetime.now()

        if log_type == "connections":
            base_path = Path(self.settings.base_dir) / "connections"
        else:
            base_path = Path(self.settings.base_dir)

        # Create year/month/day structure
        year_dir = base_path / str(today.year)
        month_dir = year_dir / f"{today.month:02d}"
        day_dir = month_dir / f"{today.day:02d}"

        day_dir.mkdir(parents=True, exist_ok=True)

        log_path = day_dir / f"{prefix}_{today.strftime('%Y-%m-%d')}.log"
        return log_path

    def _setup_loggers(self):
        """Setup application loggers"""

        # Formato común para todos los logs
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Main application logger
        self.app_logger = logging.getLogger('KFCBot')
        self.app_logger.setLevel(getattr(logging, self.settings.log_level))
        self.app_logger.propagate = False

        app_handler = logging.FileHandler(
            self._get_log_path('app', 'application'),
            encoding='utf-8'
        )
        app_handler.setFormatter(formatter)
        self.app_logger.addHandler(app_handler)

        # Console handler for development
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.app_logger.addHandler(console_handler)

        # Reprints logger
        self.reprints_logger = logging.getLogger('KFCReprints')
        self.reprints_logger.setLevel(logging.INFO)
        self.reprints_logger.propagate = False

        reprints_handler = logging.FileHandler(
            self._get_log_path('reprints', 'reimpresiones'),
            encoding='utf-8'
        )
        reprints_handler.setFormatter(formatter)
        self.reprints_logger.addHandler(reprints_handler)

        # Connections logger
        self.connections_logger = logging.getLogger('KFCConnections')
        self.connections_logger.setLevel(logging.INFO)
        self.connections_logger.propagate = False

        connections_handler = logging.FileHandler(
            self._get_log_path('connections', 'conexiones'),
            encoding='utf-8'
        )

        connections_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - User: %(username)s (ID: %(user_id)s) - Store: %(store_code)s - Action: %(action)s'
        )
        connections_handler.setFormatter(connections_formatter)
        self.connections_logger.addHandler(connections_handler)

        print("✅ Loggers configurados correctamente")

    def log_connection(self, user_id: int, username: str, store_code: str, action: str):
        """Log user connection activity"""
        try:
            self.connections_logger.info(
                '',
                extra={
                    'user_id': user_id,
                    'username': username or 'Sin nombre',
                    'store_code': store_code or 'Sin tienda',
                    'action': action
                }
            )
        except Exception as e:
            print(f"⚠️ Error logueando conexión: {e}")

    def log_reprint(self, message: str):
        """Log reprint activity"""
        try:
            self.reprints_logger.info(message)
        except Exception as e:
            print(f"⚠️ Error logueando reimpresión: {e}")

    def info(self, message: str):
        """Log info message"""
        try:
            self.app_logger.info(message)
        except Exception as e:
            print(f"⚠️ Error logueando info: {e}")

    def error(self, message: str):
        """Log error message"""
        try:
            self.app_logger.error(message)
        except Exception as e:
            print(f"⚠️ Error logueando error: {e}")

    def warning(self, message: str):
        """Log warning message"""
        try:
            self.app_logger.warning(message)
        except Exception as e:
            print(f"⚠️ Error logueando warning: {e}")

    def debug(self, message: str):
        """Log debug message"""
        try:
            self.app_logger.debug(message)
        except Exception as e:
            print(f"⚠️ Error logueando debug: {e}")


# Global logger instance
logger = StructuredLogger()