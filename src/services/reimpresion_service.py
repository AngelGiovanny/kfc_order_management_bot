# src/services/reimpresion_service.py
import requests
import logging
from typing import Dict, Any
import pyodbc
from src.config.settings import settings

logger = logging.getLogger(__name__)


class ReimpresionService:
    def __init__(self):
        self.url_api = settings.print.api_url
        self.db_config = settings.database

    def get_db_connection(self):
        """Crear conexión a la base de datos"""
        try:
            connection_string = (
                f"DRIVER={self.db_config.driver};"
                f"SERVER=10.101.2.20;"
                f"DATABASE=MAXPOINT_Local;"
                f"UID={self.db_config.user};"
                f"PWD={self.db_config.password};"
                f"Timeout={self.db_config.timeout};"
            )
            return pyodbc.connect(connection_string)
        except Exception as e:
            logger.error(f"Error creando conexión: {str(e)}")
            return None

    def reimprimir_documento(self, cfac_id: str, tipo_documento: str, ip_estacion: str = None) -> Dict[str, Any]:
        """
        Sistema de reimpresión con fallbacks
        """
        try:
            logger.info(f"Iniciando reimpresión: {cfac_id} - {tipo_documento}")

            # Método 1: Consulta directa
            resultado = self._metodo_consulta_directa(cfac_id, tipo_documento)

            if not resultado.get('success'):
                logger.info("Método 1 falló, intentando Método 2...")
                # Método 2: Stored Procedure
                resultado = self._metodo_stored_procedure(cfac_id, tipo_documento, ip_estacion)

            if not resultado.get('success'):
                logger.info("Método 2 falló, intentando Método 3...")
                # Método 3: USP final
                resultado = self._metodo_usp_final(cfac_id, tipo_documento)

            if not resultado.get('success'):
                logger.error("Todos los métodos fallaron")
                resultado = self._mensaje_soporte(cfac_id)

            # Registrar constancia
            self._registrar_constancia(cfac_id, tipo_documento, resultado)

            return resultado

        except Exception as e:
            logger.error(f"Error en reimpresión: {str(e)}")
            return {
                "success": False,
                "error": f"Error general: {str(e)}",
                "requires_support": True
            }

    def _metodo_consulta_directa(self, cfac_id: str, tipo_documento: str) -> Dict[str, Any]:
        """Método 1: Consulta directa"""
        connection = None
        try:
            connection = self.get_db_connection()
            if not connection:
                return {"success": False, "error": "No se pudo conectar a la base de datos"}

            cursor = connection.cursor()

            # Determinar query según tipo de documento
            if tipo_documento == 'factura':
                query = """
                SELECT imp_url, Canal_MovimientoVarchar1 
                FROM Canal_Movimiento 
                WHERE Canal_MovimientoVarchar3 LIKE ? 
                AND imp_varchar1 like '%factura%'
                """
            elif tipo_documento == 'nota_credito':
                query = """
                SELECT imp_url, Canal_MovimientoVarchar1 
                FROM Canal_Movimiento 
                WHERE Canal_MovimientoVarchar3 LIKE ? 
                AND imp_varchar1 like '%nota_credito%'
                """
            elif tipo_documento == 'comanda':
                query = """
                SELECT imp_url, Canal_MovimientoVarchar1 
                FROM Canal_Movimiento 
                WHERE Canal_MovimientoVarchar3 LIKE ? 
                AND imp_varchar1 like '%orden%'
                """
            else:
                return {"success": False, "error": "Tipo de documento no válido"}

            cursor.execute(query, '%' + cfac_id + '%')
            result = cursor.fetchone()

            if result:
                imp_url, canal_movimiento = result
                logger.info(f"Registro encontrado en Canal_Movimiento: {imp_url}")

                datos_impresion = {
                    "url_impresora": imp_url,
                    "documento": canal_movimiento,
                    "cfac_id": cfac_id,
                    "tipo": tipo_documento,
                    "reimpresion": True
                }

                return self._enviar_a_impresora(datos_impresion)
            else:
                return {"success": False, "error": "No se encontró registro en Canal_Movimiento"}

        except Exception as e:
            logger.error(f"Error en método 1 (consulta directa): {str(e)}")
            return {"success": False, "error": str(e)}
        finally:
            if connection:
                connection.close()

    def _metodo_stored_procedure(self, cfac_id: str, tipo_documento: str, ip_estacion: str) -> Dict[str, Any]:
        """Método 2: Stored Procedure"""
        connection = None
        try:
            if not ip_estacion:
                return {"success": False, "error": "IP de estación requerida para este método"}

            connection = self.get_db_connection()
            if not connection:
                return {"success": False, "error": "No se pudo conectar a la base de datos"}

            cursor = connection.cursor()

            sp_query = """
            DECLARE @impresiones TABLE
            (
                numeroImpresiones   INT,
                tipo			    VARCHAR(50), 
                impresora		    VARCHAR(50), 
                formatoXML	        NVARCHAR(MAX), 
                jsonData		    NVARCHAR(MAX), 
                jsonRegistros	    NVARCHAR(MAX)
            );

            INSERT INTO @impresiones
            EXEC [facturacion].[IAE_TipoFacturacion] ?, ?

            SELECT 
                '{"numeroImpresiones": '+ CONVERT(VARCHAR,numeroImpresiones) +', "tipo": "'+ tipo +'", "idImpresora": "'+ impresora +'", "idPlantilla": "'+ REPLACE(formatoXML,'/\\\\/g','') +'", "data": '+ jsonData +', "registros": '+ jsonRegistros +' }'
            FROM @impresiones
            """

            cursor.execute(sp_query, cfac_id, ip_estacion)
            result = cursor.fetchone()

            if result and result[0]:
                datos_json = result[0]
                logger.info("SP [facturacion].[IAE_TipoFacturacion] ejecutado exitosamente")

                datos_impresion = {
                    "datos_sp": datos_json,
                    "cfac_id": cfac_id,
                    "tipo": tipo_documento,
                    "reimpresion": True
                }

                return self._enviar_a_impresora(datos_impresion)
            else:
                return {"success": False, "error": "SP no retornó datos"}

        except Exception as e:
            logger.error(f"Error en método 2 (stored procedure): {str(e)}")
            return {"success": False, "error": str(e)}
        finally:
            if connection:
                connection.close()

    def _metodo_usp_final(self, cfac_id: str, tipo_documento: str) -> Dict[str, Any]:
        """Método 3: USP final"""
        connection = None
        try:
            connection = self.get_db_connection()
            if not connection:
                return {"success": False, "error": "No se pudo conectar a la base de datos"}

            cursor = connection.cursor()

            # Determinar tipo de comprobante
            tipo_comprobante = 'F'  # Factura por defecto
            if tipo_documento == 'nota_credito':
                tipo_comprobante = 'C'
            elif tipo_documento == 'comanda':
                tipo_comprobante = 'O'

            # Ejecutar USP final
            usp_query = "EXEC [facturacion].[USP_impresiondinamica_factura] ?, ?"

            cursor.execute(usp_query, cfac_id, tipo_comprobante)
            result = cursor.fetchall()

            if result:
                logger.info("USP [facturacion].[USP_impresiondinamica_factura] ejecutado exitosamente")

                # Procesar resultado del USP
                html_data = {
                    'html': result[0][0] if len(result) > 0 and result[0][0] else '',
                    'html3': result[0][1] if len(result) > 0 and result[0][1] else '',
                    'html2': result[0][2] if len(result) > 0 and result[0][2] else '',
                    'htmlf': result[0][3] if len(result) > 0 and result[0][3] else '',
                    'codigoQR': result[0][4] if len(result) > 0 and result[0][4] else ''
                }

                datos_impresion = {
                    "html_content": html_data,
                    "cfac_id": cfac_id,
                    "tipo": tipo_documento,
                    "reimpresion": True,
                    "metodo": "usp_final"
                }

                return self._enviar_a_impresora(datos_impresion)
            else:
                return {"success": False, "error": "USP no retornó datos"}

        except Exception as e:
            logger.error(f"Error en método 3 (USP final): {str(e)}")
            return {"success": False, "error": str(e)}
        finally:
            if connection:
                connection.close()

    def _enviar_a_impresora(self, datos: Dict) -> Dict[str, Any]:
        """Enviar a la API de impresión"""
        try:
            logger.info(f"Enviando a API de impresión: {self.url_api}")

            response = requests.post(
                self.url_api,
                json=datos,
                timeout=30,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code == 200:
                respuesta_api = response.json()
                logger.info("✅ API de impresión respondió exitosamente")
                return {
                    "success": True,
                    "message": "Impresión enviada exitosamente",
                    "api_response": respuesta_api,
                    "constancia": "RE IMPRESIÓN DE DOCUMENTO"
                }
            else:
                logger.error(f"❌ Error API impresión: {response.status_code}")
                return {
                    "success": False,
                    "error": f"Error en API: {response.status_code}",
                    "api_response": response.text
                }

        except requests.exceptions.Timeout:
            logger.error("⏰ Timeout en API de impresión")
            return {"success": False, "error": "Timeout en conexión con API de impresión"}
        except requests.exceptions.ConnectionError:
            logger.error("🔌 Error de conexión con API de impresión")
            return {"success": False, "error": "No se pudo conectar con API de impresión"}
        except Exception as e:
            logger.error(f"❌ Error inesperado en API: {str(e)}")
            return {"success": False, "error": f"Error de conexión: {str(e)}"}

    def _mensaje_soporte(self, cfac_id: str) -> Dict[str, Any]:
        """Mensaje cuando todo falla"""
        return {
            "success": False,
            "message": f"NO SE PUDO PROCESAR LA IMPRESIÓN para {cfac_id}. Contacte con Soporte Técnico.",
            "requires_support": True,
            "constancia": "FALLO DE IMPRESIÓN - CONTACTAR SOPORTE"
        }

    def _registrar_constancia(self, cfac_id: str, tipo_documento: str, resultado: Dict):
        """Registrar constancia de reimpresión"""
        try:
            constancia = "RE IMPRESIÓN DE DOCUMENTO" if resultado.get('success') else "FALLO EN REIMPRESIÓN"
            logger.info(f"📝 Constancia: {constancia} para {cfac_id} - {tipo_documento}")
        except Exception as e:
            logger.error(f"Error registrando constancia: {str(e)}")