# src/handlers/reprint_handler.py
import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from src.services.impresion_service import ImpresionService

logger = logging.getLogger(__name__)


class ReprintHandler:
    def __init__(self):
        self.impresion_service = ImpresionService()

    async def handle_reprint_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejar comando de reimpresión /reimprimir"""
        try:
            # Obtener parámetros del comando
            if not context.args or len(context.args) < 2:
                await update.message.reply_text(
                    "❌ Formato incorrecto. Use:\n"
                    "/reimprimir <cfac_id> <tipo_documento> [ip_estacion]\n\n"
                    "Ejemplos:\n"
                    "/reimprimir F001-123456 factura\n"
                    "/reimprimir NC001-789012 nota_credito\n"
                    "/reimprimir C001-345678 comanda 192.168.101.100"
                )
                return

            cfac_id = context.args[0]
            tipo_documento = context.args[1].lower()
            ip_estacion = context.args[2] if len(context.args) > 2 else None

            # Validar tipo de documento
            if tipo_documento not in ['factura', 'nota_credito', 'comanda']:
                await update.message.reply_text(
                    "❌ Tipo de documento no válido. Use: factura, nota_credito o comanda"
                )
                return

            # Enviar mensaje de procesamiento
            processing_msg = await update.message.reply_text(
                f"🔄 Procesando reimpresión de {tipo_documento}...\n"
                f"Documento: {cfac_id}"
            )

            # Ejecutar reimpresión
            resultado = self.impresion_service.reimprimir_documento(cfac_id, tipo_documento, ip_estacion)

            # Enviar resultado
            if resultado.get('success'):
                await processing_msg.edit_text(
                    f"✅ {resultado.get('message', 'Impresión exitosa')}\n"
                    f"📄 Documento: {cfac_id}\n"
                    f"📋 Constancia: {resultado.get('constancia', 'RE IMPRESIÓN DE DOCUMENTO')}\n"
                    f"🔧 Método: {resultado.get('method', 'directo')}"
                )
            else:
                error_msg = (
                    f"❌ {resultado.get('message', 'Error en impresión')}\n"
                    f"📄 Documento: {cfac_id}\n"
                    f"⚠️ Error: {resultado.get('error', 'Desconocido')}"
                )

                if resultado.get('requires_support'):
                    error_msg += "\n\n🚨 **CONTACTE CON SOPORTE TÉCNICO**"

                await processing_msg.edit_text(error_msg)

        except Exception as e:
            logger.error(f"Error en comando reimprimir: {str(e)}")
            await update.message.reply_text(
                f"❌ Error procesando comando: {str(e)}\n"
                "Por favor contacte con soporte técnico."
            )

    async def handle_reprint_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejar mensajes de reimpresión en formato libre"""
        try:
            message_text = update.message.text.strip()

            # Parsear mensaje (formato: "reimprimir CFAC123 factura")
            parts = message_text.split()
            if len(parts) < 3 or parts[0].lower() not in ['reimprimir', 'imprimir']:
                return  # No es un comando de reimpresión

            cfac_id = parts[1]
            tipo_documento = parts[2].lower()
            ip_estacion = parts[3] if len(parts) > 3 else None

            # Validaciones
            if tipo_documento not in ['factura', 'nota_credito', 'comanda']:
                await update.message.reply_text("❌ Tipo de documento no válido")
                return

            # Procesar reimpresión
            processing_msg = await update.message.reply_text(f"🔄 Procesando {cfac_id}...")
            resultado = self.impresion_service.reimprimir_documento(cfac_id, tipo_documento, ip_estacion)

            # Responder resultado
            if resultado.get('success'):
                await processing_msg.edit_text(f"✅ {resultado.get('message')}")
            else:
                response = f"❌ {resultado.get('message')}"
                if resultado.get('requires_support'):
                    response += "\n🚨 **CONTACTE CON SOPORTE**"
                await processing_msg.edit_text(response)

        except Exception as e:
            logger.error(f"Error en mensaje reimpresión: {str(e)}")

    def get_handlers(self):
        """Retornar los handlers para registrar en el bot"""
        return [
            CommandHandler("reimprimir", self.handle_reprint_command),
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_reprint_message)
        ]