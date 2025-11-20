import json
from src.database.connection import db_manager
from src.utils.logger import logger


class ReprintHandlers:
    @staticmethod
    async def process_json_reprint(store_code: str, json_data: dict):
        """Process reprint from JSON data"""
        try:
            # Extract data from JSON
            document_type = json_data.get('tipo')
            document_id = json_data.get('document_id')
            printer_id = json_data.get('idImpresora')
            template_id = json_data.get('idPlantilla')

            if not all([document_type, document_id, printer_id]):
                return {
                    'success': False,
                    'message': 'Datos JSON incompletos'
                }

            # Log JSON reprint
            logger.log_reprint(
                f'Re-impresión JSON - Tipo: {document_type}, '
                f'ID: {document_id}, Impresora: {printer_id}'
            )

            # Process reprint based on type
            if document_type == 'factura':
                return await ReprintHandlers._print_invoice(store_code, document_id, printer_id)
            elif document_type == 'nota_credito':
                return await ReprintHandlers._print_credit_note(store_code, document_id, printer_id)
            elif document_type == 'comanda':
                return await ReprintHandlers._print_comanda(store_code, document_id, printer_id)
            else:
                return {
                    'success': False,
                    'message': f'Tipo de documento no soportado: {document_type}'
                }

        except Exception as e:
            logger.error(f"Error processing JSON reprint: {str(e)}")
            return {
                'success': False,
                'message': f'Error procesando re-impresión: {str(e)}'
            }

    @staticmethod
    async def _print_invoice(store_code: str, document_id: str, printer_id: str):
        """Print invoice using stored procedure"""
        try:
            # Execute print stored procedure
            result = db_manager.execute_query(
                store_code,
                "EXEC facturacion.USP_impresiondinamica_factura @cfac_id = ?, @tipo_comprobante = 'F'",
                (document_id,)
            )

            return {
                'success': True,
                'message': f'Factura {document_id} enviada a impresora {printer_id}',
                'printer': printer_id
            }

        except Exception as e:
            logger.error(f"Error printing invoice: {str(e)}")
            return {
                'success': False,
                'message': f'Error imprimiendo factura: {str(e)}'
            }

    @staticmethod
    async def _print_credit_note(store_code: str, document_id: str, printer_id: str):
        """Print credit note using stored procedure"""
        try:
            result = db_manager.execute_query(
                store_code,
                "EXEC facturacion.USP_impresiondinamica_factura @cfac_id = ?, @tipo_comprobante = 'N'",
                (document_id,)
            )

            return {
                'success': True,
                'message': f'Nota de crédito {document_id} enviada a impresora {printer_id}',
                'printer': printer_id
            }

        except Exception as e:
            logger.error(f"Error printing credit note: {str(e)}")
            return {
                'success': False,
                'message': f'Error imprimiendo nota de crédito: {str(e)}'
            }

    @staticmethod
    async def _print_comanda(store_code: str, document_id: str, printer_id: str):
        """Print comanda"""
        try:
            # Get comanda data
            result = db_manager.execute_query(
                store_code,
                "SELECT IDCabeceraordenPedido FROM Cabecera_Factura WHERE cfac_id = ?",
                (document_id,)
            )

            if result:
                odp_id = result[0][0]

                # Execute comanda print procedure
                db_manager.execute_query(
                    store_code,
                    "EXEC ordenpedido.USP_impresion_orden_pedido @odp_id = ?",
                    (odp_id,)
                )

                return {
                    'success': True,
                    'message': f'Comanda {document_id} enviada a impresora {printer_id}',
                    'printer': printer_id
                }
            else:
                return {
                    'success': False,
                    'message': f'No se encontró comanda para ID {document_id}'
                }

        except Exception as e:
            logger.error(f"Error printing comanda: {str(e)}")
            return {
                'success': False,
                'message': f'Error imprimiendo comanda: {str(e)}'
            }