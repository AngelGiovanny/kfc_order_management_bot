from typing import Optional, List, Tuple
from src.database.connection import db_manager
from src.database.queries import *
from src.utils.logger import logger
import time


class OrderService:
    @staticmethod
    def validate_store_code(store_code: str) -> bool:
        """Validate store code is within range - MÁS FLEXIBLE"""
        return store_code.startswith('K') and len(store_code) >= 4

    @staticmethod
    def _get_store_ip(store_code: str) -> str:
        """Get proper IP address for store - CORREGIDO CON TERCER OCTETO NUMÉRICO"""
        # Extraer solo números del código de tienda (ej: "080" -> "80", "100" -> "100")
        store_number = ''.join(filter(str.isdigit, store_code))

        # Remover ceros a la izquierda para el tercer octeto
        # K002 -> 2, K080 -> 80, K100 -> 100
        store_number_int = int(store_number) if store_number else 0

        return f'10.101.{store_number_int}.20'

    @staticmethod
    def get_order_status(store_code: str, order_id: str) -> Optional[Tuple]:
        """Get order status with motorized information"""
        try:
            start_time = time.time()

            results = db_manager.execute_query(
                store_code,
                ORDER_STATUS_QUERY,
                (order_id, order_id)
            )

            elapsed = time.time() - start_time
            if elapsed > 2:
                logger.warning(f"Consulta de estado lenta: {elapsed:.2f}s")

            if results:
                logger.info(f"✅ Orden {order_id} encontrada en {store_code} ({elapsed:.2f}s)")
                return results[0]
            else:
                logger.warning(f"⚠️ Orden {order_id} no encontrada en {store_code}")
                return None

        except Exception as e:
            logger.error(f"❌ Error obteniendo estado orden {order_id}: {str(e)}")
            raise

    @staticmethod
    def audit_order(store_code: str, order_id: str) -> List[Tuple]:
        """Audit order with complete history"""
        try:
            start_time = time.time()

            results = db_manager.execute_query(
                store_code,
                ORDER_AUDIT_QUERY,
                (f'%{order_id}%',)
            )

            elapsed = time.time() - start_time
            logger.info(f"Auditoría completada en {elapsed:.2f}s: {len(results)} registros")
            return results

        except Exception as e:
            logger.error(f"Error en auditoría orden {order_id}: {str(e)}")
            raise

    @staticmethod
    def get_associated_code(store_code: str, cfac_id: str) -> Optional[str]:
        """Get associated code for a given invoice ID - VERSIÓN ROBUSTA"""
        try:
            start_time = time.time()

            # Consulta que busca en ambas tablas y toma el primer resultado válido
            query = """
            SELECT TOP 1 codigo_app 
            FROM (
                SELECT codigo_app, 1 as priority 
                FROM Cabecera_App WITH(NOLOCK) 
                WHERE cfac_id = ? AND codigo_app IS NOT NULL

                UNION ALL

                SELECT codigo_app, 2 as priority 
                FROM pickup_cabecera_pedidos WITH(NOLOCK) 
                WHERE cfac_id = ? AND codigo_app IS NOT NULL
            ) AS combined
            ORDER BY priority
            """

            results = db_manager.execute_query(
                store_code,
                query,
                (cfac_id, cfac_id)
            )

            elapsed = time.time() - start_time

            if results and results[0][0]:
                logger.info(f"✅ Código asociado encontrado en {elapsed:.2f}s: {results[0][0]}")
                return results[0][0]

            logger.warning(f"⚠️ No se encontró código asociado para {cfac_id} en ninguna tabla")
            return None

        except Exception as e:
            logger.error(f"❌ Error obteniendo código asociado para {cfac_id}: {str(e)}")
            return None
    @staticmethod
    def get_comanda_url(store_code: str, cfac_id: str) -> Optional[str]:
        """Get comanda URL - CORREGIDO CON IPS PROPIAS"""
        try:
            start_time = time.time()

            results = db_manager.execute_query(
                store_code,
                COMANDA_URL_QUERY,
                (cfac_id,)
            )

            elapsed = time.time() - start_time

            if results:
                odp_id = results[0][0]

                # Usar la función corregida para obtener IP
                server_ip = OrderService._get_store_ip(store_code)

                url = f"http://{server_ip}:880/PoS/ordenpedido/impresion/imprimir_ordenpedido.php?odp_id={odp_id}&tipoServicio=2&canalImpresion=0&guardaOrden=0&numeroCuenta=1"

                logger.info(f"✅ URL comanda generada en {elapsed:.2f}s: {url}")
                return url

            logger.warning(f"⚠️ No se encontró comanda para {cfac_id}")
            return None

        except Exception as e:
            logger.error(f"Error obteniendo comanda {cfac_id}: {str(e)}")
            raise

    @staticmethod
    def test_store_connection(store_code: str) -> bool:
        """Test store connection quickly"""
        try:
            start_time = time.time()

            with db_manager.get_connection(store_code):
                pass  # Solo probar conexión

            elapsed = time.time() - start_time
            logger.info(f"✅ Conexión testeada a {store_code} en {elapsed:.2f}s")
            return True

        except Exception as e:
            logger.error(f"❌ Falló test conexión a {store_code}: {str(e)}")
            return False

    @staticmethod
    def format_order_status_response(status: Tuple, order_id: str) -> str:
        """Format order status response with visual elements"""
        if len(status) == 6:  # With motorized info
            response = (
                f"📦 *Estado de Orden* 🚚\n\n"
                f"🔢 **Código:** `{status[0]}`\n"
                f"📊 **Estado:** `{status[1]}`\n"
                f"🧾 **Factura ID:** `{status[2]}`\n"
                f"📱 **Medio:** `{status[3]}`\n"
                f"🕐 **Fecha:** `{status[4].strftime('%Y-%m-%d %H:%M:%S')}`\n"
                f"🚚 **Motorizado:** `{status[5]}`\n\n"
                f"✅ *Información actualizada*"
            )
        else:
            response = (
                f"📦 *Estado de Orden* 🚚\n\n"
                f"🔢 **Código:** `{order_id}`\n"
                f"📊 **Estado:** `{status[1]}`\n"
                f"🧾 **Factura ID:** `{status[2]}`\n"
                f"🚚 **Motorizado:** `{status[5] if len(status) > 5 else 'No asignado'}`\n\n"
                f"✅ *Información encontrada*"
            )
        return response

    @staticmethod
    def format_audit_response(audit: List[Tuple], order_id: str) -> str:
        """Format audit response with visual elements"""
        if not audit:
            return (
                f"📊 *Auditoría de Orden* 📋\n\n"
                f"🔢 **Código:** `{order_id}`\n\n"
                f"❌ *No se encontró historial de auditoría*\n\n"
                f"💡 **Posibles causas:**\n"
                f"• La orden es muy reciente\n"
                f"• No hay cambios de estado registrados\n"
                f"• La orden no existe en el sistema"
            )

        detalles = []
        for i, row in enumerate(audit, 1):
            detalle = (
                f"**{i}. {row[1]}**\n"
                f"   🕐 {row[2].strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"   🚚 {row[3]}\n"
            )
            detalles.append(detalle)

        response = (
            f"📊 *Auditoría de Orden* 📋\n\n"
            f"🔢 **Código:** `{order_id}`\n"
            f"📈 **Total de registros:** `{len(audit)}`\n\n"
            f"🔄 **Historial de estados:**\n"
            f"{''.join(detalles)}\n"
            f"✅ *Auditoría completada*"
        )
        return response