import requests
import json
from typing import Optional, Dict, Any
import time

from src.config.settings import settings
from src.database.connection import db_manager
from src.utils.logger import logger


class PrintService:
    def __init__(self):
        self.settings = settings.print

    def _get_store_ip(self, store_code: str) -> str:
        """Get proper IP address for store"""
        store_number = ''.join(filter(str.isdigit, store_code))
        store_number_int = int(store_number) if store_number else 0
        return f'10.101.{store_number_int}.20'

    def _get_print_url(self, document_type: str, store_code: str, document_id: str) -> Optional[str]:
        """Generate print URL based on document type"""
        try:
            server_ip = self._get_store_ip(store_code)
            base_url = f"http://{server_ip}:880"

            if document_type == 'factura':
                url = f"{base_url}/pos/facturacion/impresion/impresion_factura.php?cfac_id={document_id}&tipo_comprobante=F&"
            elif document_type == 'nota_credito':
                url = f"{base_url}/pos/facturacion/impresion/impresion_factura.php?cfac_id={document_id}&tipo_comprobante=N&"
            elif document_type == 'comanda':
                # Usar OrderService para obtener URL de comanda
                from src.services.order_service import OrderService
                url = OrderService.get_comanda_url(store_code, document_id)
            else:
                return None

            logger.info(f"🌐 URL generada para {document_type}: {url}")
            return url

        except Exception as e:
            logger.error(f"Error generating print URL: {str(e)}")
            return None

    async def _generate_json_with_sp(self, store_code: str, document_id: str) -> Dict[str, Any]:
        """PRIMER INTENTO: Generar JSON usando stored procedure"""
        try:
            # Ejecutar el stored procedure que genera el JSON
            sp_query = """
            DECLARE @impresiones TABLE
            (
                numeroImpresiones   INT,
                tipo                VARCHAR(50), 
                impresora           VARCHAR(50), 
                formatoXML          NVARCHAR(MAX), 
                jsonData            NVARCHAR(MAX), 
                jsonRegistros       NVARCHAR(MAX)
            );

            INSERT INTO @impresiones
            EXEC [facturacion].[IAE_TipoFacturacion] ?, 'IP_estacion'

            SELECT 
                '{"numeroImpresiones": '+ CONVERT(VARCHAR,numeroImpresiones) +', "tipo": "'+ tipo +'", "idImpresora": "'+ impresora +'", "idPlantilla": "'+ REPLACE(formatoXML,'/\\/g','') +'", "data": '+ jsonData +', "registros": '+ jsonRegistros +' }' as json_output
            FROM @impresiones
            """

            logger.info(f"🔧 Ejecutando SP para generar JSON: {document_id}")
            results = db_manager.execute_query(store_code, sp_query, (document_id,))

            if results and results[0][0]:
                json_data = results[0][0]
                logger.info("✅ JSON generado exitosamente por SP")
                return {
                    'success': True,
                    'json_data': json_data
                }
            else:
                logger.warning("❌ No se generó JSON desde el stored procedure")
                return {
                    'success': False,
                    'message': 'No se generó JSON desde el stored procedure'
                }

        except Exception as e:
            logger.error(f"❌ Error generando JSON con SP: {str(e)}")
            return {
                'success': False,
                'message': f'Error en stored procedure: {str(e)}'
            }

    async def _send_to_print_api(self, json_data: str) -> Dict[str, Any]:
        """Enviar JSON a API de impresión"""
        try:
            # Parsear el JSON
            print_data = json.loads(json_data)
            printer_id = print_data.get('idImpresora', 'desconocida')

            # Enviar a la API de impresión
            logger.info(f"📤 Enviando a API de impresión: {self.settings.api_url}")

            response = requests.post(
                self.settings.api_url,
                json=print_data,
                timeout=30,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code == 200:
                logger.info("✅ Impresión enviada exitosamente vía API")
                return {
                    'success': True,
                    'printer': printer_id
                }
            else:
                logger.error(f"❌ Error en API: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'message': f'Error en API de impresión: {response.status_code}'
                }

        except requests.exceptions.Timeout:
            logger.error("⏰ Timeout en API de impresión")
            return {
                'success': False,
                'message': 'Timeout en la conexión con API de impresión'
            }
        except requests.exceptions.ConnectionError:
            logger.error("🌐 Error de conexión con API")
            return {
                'success': False,
                'message': 'Error de conexión con API de impresión'
            }
        except Exception as e:
            logger.error(f"❌ Error enviando a API: {str(e)}")
            return {
                'success': False,
                'message': f'Error de conexión con API: {str(e)}'
            }

    async def _execute_print_sp(self, store_code: str, document_type: str, document_id: str) -> Dict[str, Any]:
        """SEGUNDO INTENTO: Ejecutar SP directo de impresión"""
        try:
            sp_name = ""
            params = ()

            if document_type in ['factura', 'nota_credito']:
                sp_name = "facturacion.USP_impresiondinamica_factura"
                tipo = 'F' if document_type == 'factura' else 'N'
                params = (document_id, tipo)
            elif document_type == 'comanda':
                # Para comanda, obtener ODP_ID primero
                results = db_manager.execute_query(
                    store_code,
                    "SELECT TOP 1 IDCabeceraordenPedido FROM Cabecera_Factura WHERE cfac_id = ?",
                    (document_id,)
                )
                if results:
                    odp_id = results[0][0]
                    sp_name = "ordenpedido.USP_impresion_orden_pedido"
                    params = (odp_id,)
                else:
                    return {
                        'success': False,
                        'message': 'No se encontró ODP_ID para la comanda'
                    }

            # Ejecutar SP directo
            logger.info(f"🔧 Ejecutando SP: {sp_name} con parámetros: {params}")
            db_manager.execute_query(
                store_code,
                f"EXEC {sp_name} {'?, ?' if len(params) == 2 else '?'}",
                params
            )

            logger.info("✅ SP ejecutado exitosamente")
            return {
                'success': True,
                'printer': 'Impresora por defecto'
            }

        except Exception as e:
            logger.error(f"❌ Error en SP directo: {str(e)}")
            return {
                'success': False,
                'message': f'Error ejecutando stored procedure: {str(e)}'
            }

    async def _analyze_print_failure(self, store_code: str, document_type: str, document_id: str) -> Dict[str, Any]:
        """Analizar por qué falló la impresión y dar mensaje claro"""
        try:
            logger.info(f"🔍 Analizando fallo de impresión para {document_type} {document_id}")

            # Verificar si el documento existe
            if document_type in ['factura', 'nota_credito']:
                check_query = "SELECT TOP 1 cfac_id FROM Cabecera_Factura WHERE cfac_id = ?"
            else:  # comanda
                check_query = "SELECT TOP 1 cfac_id FROM Cabecera_Factura WHERE cfac_id = ?"

            results = db_manager.execute_query(store_code, check_query, (document_id,))

            if not results:
                return {
                    'success': False,
                    'message': f"❌ *Documento no encontrado* 📭\n\n"
                               f"**Tipo:** {document_type.title()}\n"
                               f"**ID:** `{document_id}`\n"
                               f"**Tienda:** `{store_code}`\n\n"
                               f"🔍 **El documento no existe en el sistema.**\n\n"
                               f"📞 **Contacte a Mesa de Servicio** para:\n"
                               f"• Verificar si el documento fue generado\n"
                               f"• Validar en sistema de facturación"
                }

            # Verificar datos en Canal_Movimiento
            cm_query = """
                SELECT TOP 1 imp_url, Canal_MovimientoVarchar1 
                FROM Canal_Movimiento WITH(NOLOCK)
                WHERE Canal_MovimientoVarchar3 LIKE ? 
                AND imp_varchar1 LIKE ?
            """

            like_pattern = f'%{document_id}%'
            doc_filter = f'%{document_type}%'

            cm_results = db_manager.execute_query(
                store_code,
                cm_query,
                (like_pattern, doc_filter)
            )

            if not cm_results:
                return {
                    'success': False,
                    'message': f"❌ *Datos de impresión no encontrados* 📄\n\n"
                               f"**Tipo:** {document_type.title()}\n"
                               f"**ID:** `{document_id}`\n"
                               f"**Tienda:** `{store_code}`\n\n"
                               f"🔧 **Posible causa:**\n"
                               f"El documento no fue registrado en el sistema de impresión\n\n"
                               f"📞 **Contacte a Mesa de Servicio** para:\n"
                               f"• Re-generar datos de impresión\n"
                               f"• Validar configuración de impresoras"
                }

            # Si llegamos aquí, hay un error desconocido
            return {
                'success': False,
                'message': f"❌ *Error desconocido en impresión* 🔧\n\n"
                           f"**Tipo:** {document_type.title()}\n"
                           f"**ID:** `{document_id}`\n"
                           f"**Tienda:** `{store_code}`\n\n"
                           f"🔄 **Se intentaron todos los métodos disponibles.**\n\n"
                           f"📞 **Contacte inmediatamente a Mesa de Servicio** y proporcione:\n"
                           f"• Código de tienda: `{store_code}`\n"
                           f"• ID del documento: `{document_id}`\n"
                           f"• Tipo: `{document_type}`\n"
                           f"• Hora: `{time.strftime('%Y-%m-%d %H:%M:%S')}`"
            }

        except Exception as e:
            logger.error(f"❌ Error en análisis de fallo: {str(e)}")
            return {
                'success': False,
                'message': f"❌ *Error crítico en análisis* ⚠️\n\n"
                           f"**Detalles:** `{str(e)}`\n\n"
                           f"📞 **Contacte urgentemente a Mesa de Servicio**"
            }

    async def send_reprint_request(self, document_type: str, store_code: str, document_id: str) -> Dict[str, Any]:
        """Send reprint request to printing service - MEJORADO CON MEJOR MANEJO DE ERRORES"""
        try:
            logger.info(f"🖨️ Iniciando re-impresión de {document_type} {document_id} en tienda {store_code}")

            # PRIMER INTENTO: Generar JSON con SP y consumir API
            logger.info("1️⃣ PRIMER INTENTO: Generando JSON con SP...")
            json_result = await self._generate_json_with_sp(store_code, document_id)

            if json_result['success']:
                logger.info("✅ JSON generado exitosamente, enviando a API...")
                api_result = await self._send_to_print_api(json_result['json_data'])
                if api_result['success']:
                    return {
                        'success': True,
                        'printer': api_result.get('printer', 'desconocida'),
                        'message': f"✅ *Re-impresión exitosa* 🎉\n\n"
                                   f"🧾 **Documento:** {document_type.title()}\n"
                                   f"🔢 **ID:** `{document_id}`\n"
                                   f"🏪 **Tienda:** `{store_code}`\n"
                                   f"🖨️ **Impresora:** {api_result.get('printer', 'desconocida')}\n\n"
                                   f"📋 *Por favor verifique la impresión*"
                    }

            # SEGUNDO INTENTO: Ejecutar SP directo de impresión
            logger.info("2️⃣ SEGUNDO INTENTO: Ejecutando SP directo...")
            sp_result = await self._execute_print_sp(store_code, document_type, document_id)

            if sp_result['success']:
                return {
                    'success': True,
                    'printer': sp_result.get('printer', 'Impresora por defecto'),
                    'message': f"✅ *Re-impresión enviada* 📤\n\n"
                               f"🧾 **Documento:** {document_type.title()}\n"
                               f"🔢 **ID:** `{document_id}`\n"
                               f"🏪 **Tienda:** `{store_code}`\n"
                               f"🖨️ **Método:** SP Directo\n\n"
                               f"📋 *Verifique la impresora por defecto*"
                }

            # TERCERA OPCIÓN: Análisis detallado del fallo
            logger.info("3️⃣ ANALIZANDO FALLO...")
            analysis = await self._analyze_print_failure(store_code, document_type, document_id)
            return analysis

        except Exception as e:
            logger.error(f"❌ Error crítico en re-impresión: {str(e)}")
            return {
                'success': False,
                'message': f"❌ *Error crítico en re-impresión*\n\n"
                           f"**Detalles:** `{str(e)}`\n\n"
                           f"📞 **Contacte a Mesa de Servicio** y proporcione:\n"
                           f"• Código: `{store_code}`\n"
                           f"• Documento: `{document_id}`\n"
                           f"• Tipo: `{document_type}`"
            }

    def get_max_reprints(self, document_type: str) -> int:
        """Get maximum allowed reprints for document type"""
        return self.settings.max_reprints.get(document_type, 1)

    # ELIMINAR métodos de generación de imágenes - ahora se usa OrderService directamente