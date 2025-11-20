import pyodbc
import threading
from contextlib import contextmanager
from typing import Optional
import time
import logging

from src.config.settings import settings
from src.utils.logger import logger


class DatabaseManager:
    def __init__(self):
        self.settings = settings.database

    def _get_store_server(self, store_code: str) -> str:
        """Get proper server name for store - CORREGIDO PARA K100+"""
        # Para todas las tiendas usar formato SRV_ (K100 -> SRV_K100)
        return f'SRV_{store_code}'

    def _get_connection_string(self, store_code: str) -> str:
        """Generate optimized connection string for store - CORREGIDO"""
        database_name = f'MAXPOINT_{store_code}'
        server_name = self._get_store_server(store_code)

        # String de conexión optimizado
        conn_str = (
            f'DRIVER={{{self.settings.driver}}};'
            f'SERVER={server_name};'
            f'DATABASE={database_name};'
            f'UID={self.settings.user};'
            f'PWD={self.settings.password};'
            f'Connection Timeout=15;'
            f'Login Timeout=10;'
            f'Query Timeout=30;'
            f'Application Name=KFC_Bot;'
        )

        logger.info(f"🔗 Conectando a: SERVER={server_name}, DATABASE={database_name}")
        return conn_str

    @contextmanager
    def get_connection(self, store_code: str):
        """Context manager for database connections with auto-close"""
        connection = None
        start_time = time.time()

        try:
            conn_str = self._get_connection_string(store_code)

            # Conexión optimizada
            connection = pyodbc.connect(conn_str, autocommit=True)
            connection.timeout = 15

            elapsed_time = time.time() - start_time
            logger.info(f"✅ Conexión exitosa a {store_code} en {elapsed_time:.2f}s")

            yield connection

        except pyodbc.OperationalError as e:
            elapsed_time = time.time() - start_time
            error_msg = str(e)

            if '53' in error_msg or 'network' in error_msg.lower():
                logger.error(f"❌ Error de red para tienda {store_code}: {error_msg}")
                raise Exception(f"🌐 *Problema de conexión detectado*\n\n"
                                f"**Tienda:** {store_code}\n"
                                f"**Error:** Servidor no disponible\n\n"
                                f"🔍 **Qué verificar:**\n"
                                f"• El código {store_code} es correcto\n"
                                f"• El servidor SRV_{store_code} está activo\n"
                                f"• La red tiene conectividad")
            elif 'login' in error_msg.lower():
                logger.error(f"❌ Error de autenticación para {store_code}: {error_msg}")
                raise Exception(f"🔐 *Error de credenciales*\n\n"
                                f"**Tienda:** {store_code}\n"
                                f"**Problema:** No se pudo autenticar\n\n"
                                f"💡 **Solución:**\n"
                                f"Contacte al administrador del sistema")
            else:
                logger.error(f"❌ Error operacional BD {store_code}: {error_msg}")
                raise Exception(f"⚙️ *Error de base de datos*\n\n"
                                f"**Tienda:** {store_code}\n"
                                f"**Detalle:** {error_msg}\n\n"
                                f"🛠️ **Acción requerida:**\n"
                                f"Contacte a Mesa de Servicio")

        except Exception as e:
            logger.error(f"❌ Error inesperado en {store_code}: {str(e)}")
            raise Exception(f"🚨 *Error inesperado*\n\n"
                            f"**Tienda:** {store_code}\n"
                            f"**Error:** {str(e)}\n\n"
                            f"📞 **Contacte a soporte técnico**")

        finally:
            if connection:
                try:
                    connection.close()
                except:
                    pass

    def execute_query(self, store_code: str, query: str, params: tuple = None, max_retries: int = 2):
        """Execute query with retry logic"""
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                with self.get_connection(store_code) as conn:
                    cursor = conn.cursor()

                    start_time = time.time()
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)

                    # Determinar si es SELECT o no
                    if query.strip().upper().startswith('SELECT'):
                        results = cursor.fetchall()
                        elapsed = time.time() - start_time

                        if elapsed > 3:  # Log queries lentas
                            logger.warning(f"⏱️ Query lenta en {store_code}: {elapsed:.2f}s")

                        return results
                    else:
                        conn.commit()
                        return cursor.rowcount

            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    wait_time = (attempt + 1) * 2  # Backoff exponencial
                    logger.warning(f"🔄 Reintento {attempt + 1} para {store_code} en {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ Fallo después de {max_retries + 1} intentos en {store_code}: {str(e)}")
                    raise last_exception


# Global database manager
db_manager = DatabaseManager()