import time
import datetime
import asyncio
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ContextTypes, MessageHandler, filters

from src.config.settings import settings
from src.config.constants import USER_STATES
from src.utils.logger import logger
from src.services.order_service import OrderService
from src.services.print_service import PrintService
from src.handlers.callbacks import CallbackHandlers
from src.services.reimpresion_service import ReimpresionService


class MessageHandlers:
    def __init__(self, callback_handlers: CallbackHandlers):
        self.order_service = OrderService()
        self.print_service = PrintService()
        self.callback_handlers = callback_handlers
        self.user_states = callback_handlers.user_states
        self.user_last_activity = callback_handlers.user_last_activity
        self.conteo_impresiones = callback_handlers.conteo_impresiones
        self.reimpresion_service = ReimpresionService()

    async def handle_reimpresion_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejar mensajes de reimpresión en formato libre - CORREGIDO"""
        try:
            message_text = update.message.text.strip()

            if not message_text:
                return False

            # Convertir a minúsculas
            lower_text = message_text.lower()

            # Verificar si es un comando de reimpresión
            if not (lower_text.startswith('reimprimir ') or lower_text.startswith('imprimir ')):
                return False

            # Dividir el mensaje
            parts = message_text.split()
            if len(parts) < 3:
                await update.message.reply_text(
                    "❌ *Formato incorrecto*\n\n"
                    "📋 **Uso:** `reimprimir <id> <tipo>`\n\n"
                    "🎯 **Ejemplos:**\n"
                    "• `reimprimir F001-123456 factura`\n"
                    "• `reimprimir NC001-789012 nota_credito`\n"
                    "• `reimprimir C001-345678 comanda`",
                    parse_mode='Markdown'
                )
                return True

            action = parts[0].lower()
            cfac_id = parts[1]
            tipo_raw = parts[2].lower()

            # Normalizar tipo
            tipo_mapping = {
                'nota_de_credito': 'nota_credito',
                'nota_credito': 'nota_credito',
                'notacredito': 'nota_credito',
                'nc': 'nota_credito',
                'fact': 'factura',
                'fac': 'factura',
                'com': 'comanda',
                'cmd': 'comanda',
                'orden': 'comanda'
            }

            tipo_documento = tipo_mapping.get(tipo_raw, tipo_raw)

            # Validar tipo
            if tipo_documento not in ['factura', 'nota_credito', 'comanda']:
                await update.message.reply_text(
                    "❌ *Tipo de documento no válido*\n\n"
                    "📋 **Tipos permitidos:**\n"
                    "• `factura`\n• `nota_credito`\n• `comanda`",
                    parse_mode='Markdown'
                )
                return True

            # Procesar reimpresión
            processing_msg = await update.message.reply_text(
                f"🔄 *Procesando {action}...*\n\n"
                f"📄 **Documento:** {cfac_id}\n"
                f"📋 **Tipo:** {tipo_documento}\n"
                f"⏳ *Por favor espere...*",
                parse_mode='Markdown'
            )

            resultado = self.reimpresion_service.reimprimir_documento(cfac_id, tipo_documento)

            if resultado.get('success'):
                await processing_msg.edit_text(
                    f"✅ *Impresión exitosa*\n\n"
                    f"📄 **Documento:** `{cfac_id}`\n"
                    f"📋 **Tipo:** {tipo_documento}\n"
                    f"📝 **Constancia:** RE IMPRESIÓN DE DOCUMENTO\n\n"
                    f"🖨️ *Documento enviado a impresora*",
                    parse_mode='Markdown'
                )
            else:
                response = f"❌ *Error en impresión*\n\n"
                response += f"📄 **Documento:** `{cfac_id}`\n"
                response += f"⚠️ **Error:** {resultado.get('error', 'Desconocido')}"

                if resultado.get('requires_support'):
                    response += "\n\n🚨 **CONTACTE CON SOPORTE TÉCNICO**"

                await processing_msg.edit_text(response, parse_mode='Markdown')

            return True

        except Exception as e:
            logger.error(f"Error en mensaje reimpresión: {str(e)}")
            await update.message.reply_text(f"❌ Error procesando reimpresión: {str(e)}")
            return True

    async def process_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process incoming messages - CORREGIDO Y ROBUSTO"""
        try:
            incoming_msg = update.message.text.strip()
            user_id = update.effective_user.id

            # 1. Primero verificar si es reimpresión
            is_reimpresion = await self.handle_reimpresion_message(update, context)
            if is_reimpresion:
                return

            # 2. Comandos de reinicio
            if incoming_msg.lower() in ['/reiniciar', 'reiniciar', 'reset']:
                self.user_states[user_id] = {'step': USER_STATES['GET_STORE_CODE']}
                await update.message.reply_text(
                    "🔄 *Reiniciando sistema...*\n\n"
                    "🔢 **Ingresa código de tienda:**\n"
                    "(Ejemplo: K002, K080, K100)",
                    parse_mode='Markdown'
                )
                return

            # 3. Verificar inactividad
            current_time = time.time()
            last_activity = self.user_last_activity.get(user_id, current_time)

            if current_time - last_activity > settings.bot.max_inactivity_time:
                await update.message.reply_text(
                    "⏰ *Sesión expirada*\n\n"
                    "🔄 Usa /start para comenzar nuevamente.",
                    parse_mode='Markdown'
                )
                self.user_states[user_id] = {'step': USER_STATES['GET_STORE_CODE']}
                self.user_last_activity[user_id] = current_time
                return

            self.user_last_activity[user_id] = current_time

            # 4. Inicializar estado si no existe
            if user_id not in self.user_states:
                self.user_states[user_id] = {'step': USER_STATES['GET_STORE_CODE']}

            state = self.user_states[user_id]

            # 5. Procesar según estado
            if state['step'] == USER_STATES['GET_STORE_CODE']:
                await self._handle_store_code(update, incoming_msg, user_id)

            elif state['step'] == USER_STATES['GET_ORDER_STATUS']:
                await self._handle_order_status(update, incoming_msg, state)

            elif state['step'] == USER_STATES['GET_ORDER_AUDIT']:
                await self._handle_order_audit(update, incoming_msg, state)

            elif state['step'] == USER_STATES['GET_INVOICE_ID']:
                await self._handle_invoice_image(update, incoming_msg, state)

            elif state['step'] == USER_STATES['GET_COMANDA_ID']:
                await self._handle_comanda_image(update, incoming_msg, state)

            elif state['step'] == USER_STATES['GET_CFAC_ID']:
                await self._handle_associated_code(update, incoming_msg, state)

            elif state['step'] == USER_STATES['GET_REPRINT_ID']:
                await self._handle_reprint_id(update, incoming_msg, state)

            elif state['step'] == USER_STATES['GET_REPRINT_REASON']:
                await self._handle_reprint_reason(update, incoming_msg, state)

            else:
                # Estado no reconocido - reiniciar
                self.user_states[user_id] = {'step': USER_STATES['GET_STORE_CODE']}
                await update.message.reply_text(
                    "🔄 *Estado no reconocido. Reiniciando...*\n\n"
                    "🔢 **Ingresa código de tienda:**\n"
                    "(Ejemplo: K002, K080, K100)",
                    parse_mode='Markdown'
                )

        except Exception as e:
            logger.error(f"Error procesando mensaje: {str(e)}")
            # Reiniciar estado en caso de error
            user_id = update.effective_user.id
            self.user_states[user_id] = {'step': USER_STATES['GET_STORE_CODE']}
            await update.message.reply_text(
                "❌ *Error procesando mensaje*\n\n"
                "🔄 *Sistema reiniciado. Ingresa código de tienda:*\n"
                "(Ejemplo: K002, K080, K100)",
                parse_mode='Markdown'
            )

    async def _handle_store_code(self, update: Update, store_code: str, user_id: int):
        """Handle store code input - CORREGIDO"""
        try:
            store_code = store_code.upper().strip()

            # Validación simple
            if not store_code.startswith('K') or len(store_code) < 3:
                await update.message.reply_text(
                    "❌ *Código incorrecto*\n\n"
                    "El formato debe empezar con **K** seguido de números.\n\n"
                    "💡 **Ejemplos válidos:**\n"
                    "`K002` `K080` `K100` `K101`\n\n"
                    "🔢 **Ingresa código correcto:**",
                    parse_mode='Markdown'
                )
                return

            processing_msg = await update.message.reply_text(
                f"🔍 *Conectando con {store_code}...*\n\n"
                f"⏳ *Por favor espere...*",
                parse_mode='Markdown'
            )

            # Test de conexión
            is_connected = await asyncio.get_event_loop().run_in_executor(
                None,
                self.order_service.test_store_connection,
                store_code
            )

            if is_connected:
                await processing_msg.edit_text(
                    f"✅ *¡Conexión exitosa!* 🎉\n\n"
                    f"🏪 **Tienda:** `{store_code}`\n\n"
                    f"📱 *Cargando menú principal...*",
                    parse_mode='Markdown'
                )

                self.user_states[user_id] = {
                    'store_code': store_code,
                    'step': USER_STATES['MAIN_MENU']
                }

                await self.callback_handlers.mostrar_menu_principal(update.message)
            else:
                await processing_msg.edit_text(
                    f"❌ *No se pudo conectar a* `{store_code}`\n\n"
                    f"🔧 **Verifica el código e intenta nuevamente:**",
                    parse_mode='Markdown'
                )

        except Exception as e:
            logger.error(f"Error en store code: {str(e)}")
            await update.message.reply_text(
                f"❌ *Error de conexión*\n\n"
                f"🔢 **Intenta con otro código:**",
                parse_mode='Markdown'
            )

    async def _handle_order_status(self, update: Update, order_id: str, state: dict):
        """Handle order status request"""
        store_code = state.get('store_code')
        if not store_code:
            await update.message.reply_text("❌ Error: No hay tienda configurada")
            state['step'] = USER_STATES['MAIN_MENU']
            await self.callback_handlers.mostrar_menu_principal(update.message)
            return

        try:
            status = self.order_service.get_order_status(store_code, order_id)
            if status:
                response_text = self.order_service.format_order_status_response(status, order_id)
                await update.message.reply_text(response_text, parse_mode='Markdown')
            else:
                await update.message.reply_text(
                    f'❌ No se encontró la orden `{order_id}` en la tienda `{store_code}`.',
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.error(f"Error getting order status: {str(e)}")
            await update.message.reply_text(
                f'❌ Error obteniendo estado: `{str(e)}`',
                parse_mode='Markdown'
            )

        state['step'] = USER_STATES['MAIN_MENU']
        await self.callback_handlers.mostrar_menu_principal(update.message)

    async def _handle_order_audit(self, update: Update, order_id: str, state: dict):
        """Handle order audit request"""
        store_code = state.get('store_code')
        if not store_code:
            await update.message.reply_text("❌ Error: No hay tienda configurada")
            state['step'] = USER_STATES['MAIN_MENU']
            await self.callback_handlers.mostrar_menu_principal(update.message)
            return

        try:
            audit = self.order_service.audit_order(store_code, order_id)
            if audit:
                response_text = self.order_service.format_audit_response(audit, order_id)
                await update.message.reply_text(response_text, parse_mode='Markdown')
            else:
                await update.message.reply_text(
                    f'❌ No se encontró auditoría para `{order_id}`',
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.error(f"Error getting order audit: {str(e)}")
            await update.message.reply_text(
                f'❌ Error obteniendo auditoría: `{str(e)}`',
                parse_mode='Markdown'
            )

        state['step'] = USER_STATES['MAIN_MENU']
        await self.callback_handlers.mostrar_menu_principal(update.message)

    async def _handle_invoice_image(self, update: Update, cfac_id: str, state: dict):
        """Handle invoice image generation"""
        store_code = state.get('store_code')
        if not store_code:
            await update.message.reply_text("❌ Error: No hay tienda configurada")
            state['step'] = USER_STATES['MAIN_MENU']
            await self.callback_handlers.mostrar_menu_principal(update.message)
            return

        try:
            processing_msg = await update.message.reply_text(
                "📸 *Generando imagen de factura...*\n\n"
                "⏳ *Por favor espere...*",
                parse_mode='Markdown'
            )

            image_buffer = await asyncio.get_event_loop().run_in_executor(
                None,
                self.order_service.generate_invoice_image,
                store_code,
                cfac_id
            )

            if image_buffer and image_buffer.getbuffer().nbytes > 100:
                await update.message.reply_photo(
                    photo=InputFile(image_buffer, filename=f"factura_{cfac_id}.png"),
                    caption=f"🧾 *Factura:* `{cfac_id}`\n🏪 *Tienda:* `{store_code}`",
                    parse_mode='Markdown'
                )
                await processing_msg.delete()
            else:
                await processing_msg.edit_text("❌ No se pudo generar la imagen de la factura")
        except Exception as e:
            logger.error(f"Error generando imagen: {str(e)}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

        state['step'] = USER_STATES['MAIN_MENU']
        await self.callback_handlers.mostrar_menu_principal(update.message)

    async def _handle_comanda_image(self, update: Update, cfac_id: str, state: dict):
        """Handle comanda image generation"""
        store_code = state.get('store_code')
        if not store_code:
            await update.message.reply_text("❌ Error: No hay tienda configurada")
            state['step'] = USER_STATES['MAIN_MENU']
            await self.callback_handlers.mostrar_menu_principal(update.message)
            return

        try:
            processing_msg = await update.message.reply_text(
                "📸 *Generando imagen de comanda...*\n\n"
                "⏳ *Por favor espere...*",
                parse_mode='Markdown'
            )

            image_buffer = await asyncio.get_event_loop().run_in_executor(
                None,
                self.order_service.generate_comanda_image,
                store_code,
                cfac_id
            )

            if image_buffer and image_buffer.getbuffer().nbytes > 100:
                await update.message.reply_photo(
                    photo=InputFile(image_buffer, filename=f"comanda_{cfac_id}.png"),
                    caption=f"🍔 *Comanda:* `{cfac_id}`\n🏪 *Tienda:* `{store_code}`",
                    parse_mode='Markdown'
                )
                await processing_msg.delete()
            else:
                await processing_msg.edit_text("❌ No se pudo generar la imagen de la comanda")
        except Exception as e:
            logger.error(f"Error generando comanda: {str(e)}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

        state['step'] = USER_STATES['MAIN_MENU']
        await self.callback_handlers.mostrar_menu_principal(update.message)

    async def _handle_associated_code(self, update: Update, cfac_id: str, state: dict):
        """Handle associated code request"""
        store_code = state.get('store_code')
        if not store_code:
            await update.message.reply_text("❌ Error: No hay tienda configurada")
            state['step'] = USER_STATES['MAIN_MENU']
            await self.callback_handlers.mostrar_menu_principal(update.message)
            return

        try:
            codigo_asociado = self.order_service.get_associated_code(store_code, cfac_id)
            if codigo_asociado:
                await update.message.reply_text(
                    f'🔍 *Código Asociado Encontrado*\n\n'
                    f'🧾 **Factura:** `{cfac_id}`\n'
                    f'🔗 **Código:** `{codigo_asociado}`\n'
                    f'🏪 **Tienda:** `{store_code}`',
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    f'❌ *No se encontró código asociado para* `{cfac_id}`',
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.error(f"Error getting associated code: {str(e)}")
            await update.message.reply_text(
                f'❌ Error: `{str(e)}`',
                parse_mode='Markdown'
            )

        state['step'] = USER_STATES['MAIN_MENU']
        await self.callback_handlers.mostrar_menu_principal(update.message)

    async def _handle_reprint_id(self, update: Update, document_id: str, state: dict):
        """Handle reprint document ID input - CORREGIDO"""
        try:
            document_type = state.get('reimpresion_tipo')

            # Validar que tenemos el tipo de documento
            if not document_type:
                await update.message.reply_text(
                    "❌ *Error: Tipo de documento no definido*\n\n"
                    "🔄 Por favor, inicia el proceso nuevamente desde el menú.",
                    parse_mode='Markdown'
                )
                state['step'] = USER_STATES['MAIN_MENU']
                await self.callback_handlers.mostrar_menu_principal(update.message)
                return

            # Validar formato del ID
            if not document_id or len(document_id.strip()) < 3:
                await update.message.reply_text(
                    "❌ *ID de documento inválido*\n\n"
                    "🔢 **Por favor, ingrese un ID válido:**",
                    parse_mode='Markdown'
                )
                return

            # Guardar ID en el estado
            state['reimpresion_id_documento'] = document_id.strip()

            await update.message.reply_text(
                f"📝 *Re-Impresión Solicitada*\n\n"
                f"📄 **Tipo:** {document_type.replace('_', ' ').title()}\n"
                f"🔢 **ID:** `{document_id}`\n\n"
                "📋 **Por favor, ingrese el motivo de la reimpresión:**\n"
                "(Ejemplo: 'No salió impreso', 'Papel atascado', 'Calidad deficiente')",
                parse_mode='Markdown'
            )
            state['step'] = USER_STATES['GET_REPRINT_REASON']

        except Exception as e:
            logger.error(f"Error en handle_reprint_id: {str(e)}")
            await update.message.reply_text(
                "❌ Error procesando ID de documento\n"
                "🔄 Volviendo al menú principal..."
            )
            state['step'] = USER_STATES['MAIN_MENU']
            await self.callback_handlers.mostrar_menu_principal(update.message)

    async def _handle_reprint_reason(self, update: Update, motivo: str, state: dict):
        """Handle reprint reason and process reprint - COMPLETAMENTE CORREGIDO"""
        try:
            document_id = state.get('reimpresion_id_documento')
            document_type = state.get('reimpresion_tipo')
            store_code = state.get('store_code')

            # Validación completa de datos
            missing_data = []
            if not document_id:
                missing_data.append("ID del documento")
            if not document_type:
                missing_data.append("tipo de documento")
            if not store_code:
                missing_data.append("código de tienda")
            if not motivo or motivo.strip() == "":
                missing_data.append("motivo de reimpresión")

            if missing_data:
                error_msg = "❌ *Error en datos de reimpresión*\n\n"
                error_msg += "**Faltan los siguientes datos:**\n"
                for data in missing_data:
                    error_msg += f"• {data}\n"
                error_msg += "\n🔄 Por favor, inicia el proceso nuevamente desde el menú."

                await update.message.reply_text(error_msg, parse_mode='Markdown')
                state['step'] = USER_STATES['MAIN_MENU']
                await self.callback_handlers.mostrar_menu_principal(update.message)
                return

            # Verificar límites de reimpresión
            reprint_key = f'{document_type}_{document_id}'
            current_count = self.conteo_impresiones.get(reprint_key, 0)
            max_reprints = self.print_service.get_max_reprints(document_type)

            if current_count >= max_reprints:
                await update.message.reply_text(
                    f'❌ *Límite de re-impresiones alcanzado*\n\n'
                    f'📄 **Documento:** `{document_id}`\n'
                    f'📋 **Tipo:** {document_type.replace("_", " ").title()}\n'
                    f'🔢 **Límite:** `{max_reprints}` re-impresión(es)\n\n'
                    f'⚠️ No se pueden realizar más re-impresiones para este documento.\n\n'
                    f'📞 **Contacte a Mesa de Servicio** para asistencia.',
                    parse_mode='Markdown'
                )
                state['step'] = USER_STATES['MAIN_MENU']
                await self.callback_handlers.mostrar_menu_principal(update.message)
                return

            # Mostrar mensaje de procesamiento
            processing_msg = await update.message.reply_text(
                f"🖨️ *Procesando re-impresión...*\n\n"
                f"📄 **Documento:** {document_type.replace('_', ' ').title()}\n"
                f"🔢 **ID:** `{document_id}`\n"
                f"🏪 **Tienda:** `{store_code}`\n"
                f"📋 **Motivo:** {motivo}\n\n"
                f"⏳ *Por favor espere...*",
                parse_mode='Markdown'
            )

            # Registrar intento de reimpresión
            log_message = (
                f'Re-impresión solicitada - '
                f'Tipo: {document_type}, '
                f'ID: {document_id}, '
                f'Motivo: {motivo}, '
                f'Tienda: {store_code}, '
                f'Usuario: {update.effective_user.username or update.effective_user.id}'
            )
            logger.info(log_message)

            # Enviar solicitud de reimpresión
            result = await self.print_service.send_reprint_request(
                document_type, store_code, document_id
            )

            # Actualizar contador si fue exitoso
            if result.get('success'):
                self.conteo_impresiones[reprint_key] = current_count + 1

            # Mostrar resultado
            await processing_msg.delete()

            if result.get('success'):
                await update.message.reply_text(
                    f'✅ *Re-impresión Exitosa*\n\n'
                    f'📄 **Documento:** `{document_id}`\n'
                    f'📋 **Tipo:** {document_type.replace("_", " ").title()}\n'
                    f'🏪 **Tienda:** `{store_code}`\n\n'
                    f'🖨️ *El documento ha sido enviado a la impresora*\n\n'
                    f'📝 **Constancia:** RE IMPRESIÓN DE DOCUMENTO',
                    parse_mode='Markdown'
                )
            else:
                error_message = (
                    f'❌ *Error en Re-impresión*\n\n'
                    f'📄 **Documento:** `{document_id}`\n'
                    f'📋 **Tipo:** {document_type.replace("_", " ").title()}\n'
                    f'🏪 **Tienda:** `{store_code}`\n\n'
                    f'⚠️ **Error:** {result.get("message", "Error desconocido")}'
                )

                if result.get('requires_support', False):
                    error_message += '\n\n🚨 **CONTACTE CON SOPORTE TÉCNICO**'

                await update.message.reply_text(error_message, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Error en handle_reprint_reason: {str(e)}")
            await update.message.reply_text(
                f"❌ *Error procesando reimpresión*\n\n"
                f"📋 **Detalles:** `{str(e)}`\n\n"
                f"🔄 Volviendo al menú principal...",
                parse_mode='Markdown'
            )
        finally:
            # Limpiar estado de reimpresión y volver al menú
            state.pop('reimpresion_id_documento', None)
            state.pop('reimpresion_tipo', None)
            state['step'] = USER_STATES['MAIN_MENU']
            await self.callback_handlers.mostrar_menu_principal(update.message)

    def get_handlers(self):
        """Get all message handlers"""
        return [
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_message)
        ]