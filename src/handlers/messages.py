import time
import datetime
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ContextTypes, MessageHandler, filters

from src.config.settings import settings
from src.config.constants import USER_STATES
from src.utils.logger import logger
from src.services.order_service import OrderService
from src.services.print_service import PrintService
from src.handlers.callbacks import CallbackHandlers


class MessageHandlers:
    def __init__(self, callback_handlers: CallbackHandlers):
        self.order_service = OrderService()
        self.print_service = PrintService()
        self.callback_handlers = callback_handlers
        self.user_states = callback_handlers.user_states
        self.user_last_activity = callback_handlers.user_last_activity
        self.conteo_impresiones = callback_handlers.conteo_impresiones

    async def process_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process incoming messages - MEJORADO CON REINICIO"""
        incoming_msg = update.message.text.strip()
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.full_name

        # Comando especial para reiniciar
        if incoming_msg.lower() in ['/reiniciar', 'reiniciar', 'reset', '/start']:
            self.user_states[user_id] = {'step': USER_STATES['GET_STORE_CODE']}
            await update.message.reply_text(
                "🔄 *Reiniciando sistema...*\n\n"
                "🔢 **Por favor, ingresa el código de tienda:**\n"
                "(Ejemplo: K002, K080, K100)",
                parse_mode='Markdown'
            )
            return

        # Check inactivity
        current_time = time.time()
        last_activity = self.user_last_activity.get(user_id, current_time)

        if current_time - last_activity > settings.bot.max_inactivity_time:
            await update.message.reply_text(
                "⏰ *Sesión expirada*\n\n"
                "Ha pasado mucho tiempo sin actividad.\n\n"
                "🔄 Usa /start para comenzar nuevamente.",
                parse_mode='Markdown'
            )
            self.user_states[user_id] = {'step': USER_STATES['GET_STORE_CODE']}
            self.user_last_activity[user_id] = current_time
            return

        self.user_last_activity[user_id] = current_time

        # Initialize user state if not exists
        if user_id not in self.user_states:
            self.user_states[user_id] = {'step': USER_STATES['GET_STORE_CODE']}

        state = self.user_states[user_id]

        try:
            if state['step'] == USER_STATES['GET_STORE_CODE']:
                await self._handle_store_code(update, incoming_msg, user_id, username)

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
                await update.message.reply_text(
                    "❓ *Estado no reconocido*\n\n"
                    "🔄 Usa /start para reiniciar la conversación.",
                    parse_mode='Markdown'
                )

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            await update.message.reply_text(
                "❌ *Error procesando solicitud*\n\n"
                "🔄 Por favor, intenta nuevamente o usa /start para reiniciar.",
                parse_mode='Markdown'
            )

    async def _handle_store_code(self, update: Update, store_code: str, user_id: int, username: str):
        """Handle store code input - MEJORADO CON REINICIO DE CONEXIÓN"""
        store_code = store_code.upper().strip()

        # Validación mejorada con mensaje amigable
        if not store_code.startswith('K') or len(store_code) < 3:
            error_message = (
                "❌ *Código incorrecto*\n\n"
                "El formato debe ser:\n"
                "• Empezar con **K**\n"
                "• Seguido de números\n"
                "• Mínimo 3 caracteres\n\n"
                "💡 **Ejemplos válidos:**\n"
                "`K002` `K080` `K100` `K101`\n\n"
                "🔢 **Por favor, ingresa el código correcto:**"
            )
            await update.message.reply_text(
                error_message,
                parse_mode='Markdown'
            )
            return

        # CERRAR CONEXIONES ANTERIORES si existen
        try:
            from src.database.connection import db_manager
            if hasattr(db_manager, 'close_connection'):
                db_manager.close_connection(store_code)
        except Exception as e:
            logger.warning(f"No se pudo cerrar conexión anterior: {e}")

        # Mostrar mensaje de procesamiento visual
        processing_msg = await update.message.reply_text(
            "🔍 *Verificando conexión con la tienda...*\n\n"
            "⏳ Esto puede tomar unos segundos",
            parse_mode='Markdown'
        )

        # Test de conexión con timeout
        try:
            # Ejecutar con timeout
            is_connected = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    self.order_service.test_store_connection,
                    store_code
                ),
                timeout=15.0
            )

            if is_connected:
                success_message = (
                    f"✅ *¡Conexión exitosa!* 🎉\n\n"
                    f"🏪 **Tienda:** `{store_code}`\n"
                    f"👤 **Usuario:** {username or 'Usuario'}\n"
                    f"🕐 **Hora:** {datetime.datetime.now().strftime('%H:%M')}\n\n"
                    "📱 *Cargando menú principal...*"
                )

                await processing_msg.edit_text(
                    success_message,
                    parse_mode='Markdown'
                )

                # LIMPIAR Y ESTABLECER NUEVO ESTADO
                self.user_states[user_id] = {
                    'store_code': store_code,
                    'step': USER_STATES['MAIN_MENU']
                }

                # Log connection
                logger.log_connection(user_id, username, store_code, "store_login")

                # Pequeña pausa para mejor UX
                await asyncio.sleep(1)

                await self.callback_handlers.mostrar_menu_principal(update.message)
            else:
                raise Exception("No se pudo establecer conexión con la base de datos")

        except asyncio.TimeoutError:
            error_message = (
                f"⏰ *Timeout de conexión* ⚠️\n\n"
                f"**Tienda:** `{store_code}`\n\n"
                f"🔧 **Posibles causas:**\n"
                f"• La tienda está fuera de línea\n"
                f"• Problemas de red\n"
                f"• El código es incorrecto\n\n"
                f"🔄 **Intenta con otro código:**"
            )
            await processing_msg.edit_text(
                error_message,
                parse_mode='Markdown'
            )
        except Exception as e:
            error_message = (
                f"❌ *No se pudo conectar* 🌐\n\n"
                f"**Tienda:** `{store_code}`\n\n"
                f"📋 **Detalles del error:**\n"
                f"`{str(e)}`\n\n"
                f"🔧 **Qué puedes hacer:**\n"
                f"• Verificar el código `{store_code}`\n"
                f"• Confirmar que la tienda esté operativa\n"
                f"• Revisar conectividad de red\n\n"
                f"🔄 **Intenta con otro código o contacta a soporte:**"
            )
            await processing_msg.edit_text(
                error_message,
                parse_mode='Markdown'
            )

    async def _handle_order_status(self, update: Update, order_id: str, state: dict):
        """Handle order status request"""
        store_code = state['store_code']

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
                f'❌ Error obteniendo estado de la orden: `{str(e)}`',
                parse_mode='Markdown'
            )

        state['step'] = USER_STATES['MAIN_MENU']
        await self.callback_handlers.mostrar_menu_principal(update.message)

    async def _handle_order_audit(self, update: Update, order_id: str, state: dict):
        """Handle order audit request"""
        store_code = state['store_code']

        try:
            audit = self.order_service.audit_order(store_code, order_id)

            if audit:
                response_text = self.order_service.format_audit_response(audit, order_id)

                # Split long messages if needed
                if len(response_text) > 4000:
                    parts = [response_text[i:i + 4000] for i in range(0, len(response_text), 4000)]
                    for part in parts:
                        await update.message.reply_text(part, parse_mode='Markdown')
                else:
                    await update.message.reply_text(response_text, parse_mode='Markdown')
            else:
                await update.message.reply_text(
                    f'❌ No se encontró auditoría para la orden `{order_id}`',
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
        """Handle invoice image generation with Selenium - MEJORADO CON ASYNCIO"""
        store_code = state['store_code']

        try:
            # Mensaje de procesamiento
            processing_msg = await update.message.reply_text(
                "📸 *Capturando imagen de la factura...*\n\n"
                "⏳ Esto puede tomar de 10-15 segundos\n"
                "🔄 *Por favor espere...*",
                parse_mode='Markdown'
            )

            # Ejecutar en thread separado para no bloquear el event loop
            image_buffer = await asyncio.get_event_loop().run_in_executor(
                None,
                self.order_service.generate_invoice_image,
                store_code,
                cfac_id
            )

            if image_buffer and image_buffer.getbuffer().nbytes > 100:
                await update.message.reply_photo(
                    photo=InputFile(image_buffer, filename=f"factura_{cfac_id}.png"),
                    caption=f"🧾 *Factura:* `{cfac_id}`\n🏪 *Tienda:* `{store_code}`\n📅 *Generado:* {datetime.datetime.now().strftime('%H:%M:%S')}",
                    parse_mode='Markdown'
                )
                await processing_msg.delete()

                # Mensaje de éxito
                await update.message.reply_text(
                    "✅ *Imagen generada exitosamente*\n\n"
                    "📋 La factura ha sido capturada y enviada.",
                    parse_mode='Markdown'
                )
            else:
                # Si falla, mostrar URL directa
                invoice_url = self.order_service.get_invoice_url(store_code, cfac_id)
                await processing_msg.edit_text(
                    f"❌ *No se pudo generar la imagen automática*\n\n"
                    f"🔗 **Acceda directamente a la factura:**\n"
                    f"`{invoice_url}`\n\n"
                    f"📞 *Si el problema persiste, contacte a soporte*",
                    parse_mode='Markdown'
                )

        except Exception as e:
            logger.error(f"Error generando imagen de factura: {str(e)}")
            invoice_url = self.order_service.get_invoice_url(store_code, cfac_id)
            await update.message.reply_text(
                f"❌ *Error generando imagen*\n\n"
                f"🔗 **Acceda directamente a la factura:**\n"
                f"`{invoice_url}`\n\n"
                f"📋 **Error:** `{str(e)}`",
                parse_mode='Markdown'
            )

        state['step'] = USER_STATES['MAIN_MENU']
        await self.callback_handlers.mostrar_menu_principal(update.message)

    async def _handle_comanda_image(self, update: Update, cfac_id: str, state: dict):
        """Handle comanda image generation with Selenium - MEJORADO CON ASYNCIO"""
        store_code = state['store_code']

        try:
            processing_msg = await update.message.reply_text(
                "📸 *Capturando imagen de la comanda...*\n\n"
                "⏳ Esto puede tomar de 10-15 segundos\n"
                "🔄 *Por favor espere...*",
                parse_mode='Markdown'
            )

            # Ejecutar en thread separado para no bloquear el event loop
            image_buffer = await asyncio.get_event_loop().run_in_executor(
                None,
                self.order_service.generate_comanda_image,
                store_code,
                cfac_id
            )

            if image_buffer and image_buffer.getbuffer().nbytes > 100:
                await update.message.reply_photo(
                    photo=InputFile(image_buffer, filename=f"comanda_{cfac_id}.png"),
                    caption=f"🍔 *Comanda:* `{cfac_id}`\n🏪 *Tienda:* `{store_code}`\n📅 *Generado:* {datetime.datetime.now().strftime('%H:%M:%S')}",
                    parse_mode='Markdown'
                )
                await processing_msg.delete()

                # Mensaje de éxito
                await update.message.reply_text(
                    "✅ *Comanda generada exitosamente*\n\n"
                    "📋 La comanda ha sido capturada y enviada.",
                    parse_mode='Markdown'
                )
            else:
                comanda_url = self.order_service.get_comanda_url(store_code, cfac_id)
                await processing_msg.edit_text(
                    f"❌ *No se pudo generar la imagen de comanda*\n\n"
                    f"🔗 **URL de comanda:**\n`{comanda_url}`\n\n"
                    f"📞 *Si el problema persiste, contacte a soporte*",
                    parse_mode='Markdown'
                )

        except Exception as e:
            logger.error(f"Error generando comanda: {str(e)}")
            comanda_url = self.order_service.get_comanda_url(store_code, cfac_id)
            if comanda_url:
                await update.message.reply_text(
                    f"❌ *Error generando imagen*\n\n"
                    f"🔗 **Acceda directamente a la comanda:**\n`{comanda_url}`\n\n"
                    f"📋 **Error:** `{str(e)}`",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    f"❌ *Error generando imagen de comanda:*\n`{str(e)}`\n\n"
                    f"📞 *Contacte a soporte técnico*",
                    parse_mode='Markdown'
                )

        state['step'] = USER_STATES['MAIN_MENU']
        await self.callback_handlers.mostrar_menu_principal(update.message)

    async def _handle_associated_code(self, update: Update, cfac_id: str, state: dict):
        """Handle associated code request"""
        store_code = state['store_code']

        try:
            codigo_asociado = self.order_service.get_associated_code(store_code, cfac_id)

            if codigo_asociado:
                await update.message.reply_text(
                    f'🔍 *Código Asociado Encontrado* ✅\n\n'
                    f'🧾 **Factura:** `{cfac_id}`\n'
                    f'🔗 **Código Asociado:** `{codigo_asociado}`\n'
                    f'🏪 **Tienda:** `{store_code}`',
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    f'❌ *Código Asociado No Encontrado*\n\n'
                    f'🧾 **Factura:** `{cfac_id}`\n'
                    f'🏪 **Tienda:** `{store_code}`\n\n'
                    f'💡 **Posibles causas:**\n'
                    f'• La factura no tiene código asociado\n'
                    f'• La factura es muy reciente\n'
                    f'• Error en la búsqueda',
                    parse_mode='Markdown'
                )

        except Exception as e:
            logger.error(f"Error getting associated code: {str(e)}")
            await update.message.reply_text(
                f'❌ *Error obteniendo código asociado*\n\n'
                f'📋 **Detalles:** `{str(e)}`\n\n'
                f'📞 *Contacte a soporte si el problema persiste*',
                parse_mode='Markdown'
            )

        state['step'] = USER_STATES['MAIN_MENU']
        await self.callback_handlers.mostrar_menu_principal(update.message)

    async def _handle_reprint_id(self, update: Update, document_id: str, state: dict):
        """Handle reprint document ID input"""
        document_type = state.get('reimpresion_tipo')

        # Validar formato del ID según el tipo
        if document_type in ['factura', 'nota_credito'] and not document_id.isdigit():
            await update.message.reply_text(
                "❌ *Formato incorrecto*\n\n"
                f"Para {document_type.replace('_', ' ').title()}, el ID debe ser numérico.\n\n"
                "🔢 **Por favor, ingrese un ID válido:**",
                parse_mode='Markdown'
            )
            return

        state['reimpresion_id_documento'] = document_id

        await update.message.reply_text(
            f"📝 *Re-Impresión Solicitada*\n\n"
            f"📄 **Tipo:** {document_type.replace('_', ' ').title()}\n"
            f"🔢 **ID:** `{document_id}`\n\n"
            "📋 **Por favor, ingrese el motivo de la reimpresión:**\n"
            "(Ejemplo: 'No salió impreso', 'Papel atascado', 'Calidad deficiente')",
            parse_mode='Markdown'
        )
        state['step'] = USER_STATES['GET_REPRINT_REASON']

    async def _handle_reprint_reason(self, update: Update, motivo: str, state: dict):
        """Handle reprint reason and process reprint"""
        document_id = state.get('reimpresion_id_documento')
        document_type = state.get('reimpresion_tipo')
        store_code = state['store_code']

        # Validar que tenemos todos los datos necesarios
        if not document_id or not document_type:
            await update.message.reply_text(
                "❌ *Error en los datos de reimpresión*\n\n"
                "🔄 Por favor, inicie el proceso nuevamente.",
                parse_mode='Markdown'
            )
            state['step'] = USER_STATES['MAIN_MENU']
            await self.callback_handlers.mostrar_menu_principal(update.message)
            return

        # Check reprint limits
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
            f"🏪 **Tienda:** `{store_code}`\n\n"
            f"⏳ *Por favor espere...*",
            parse_mode='Markdown'
        )

        # Log reprint attempt
        log_message = (
            f'Re-impresión solicitada - Tipo: {document_type}, '
            f'ID: {document_id}, Motivo: {motivo}, '
            f'Tienda: {store_code}, Usuario: {update.effective_user.username}'
        )
        logger.log_reprint(log_message)

        # Send reprint request
        result = await self.print_service.send_reprint_request(
            document_type, store_code, document_id
        )

        # Update counter if successful
        if result['success']:
            self.conteo_impresiones[reprint_key] = current_count + 1

        await processing_msg.delete()
        await update.message.reply_text(
            f'🖨️ *Resultado Re-Impresión*\n\n{result["message"]}',
            parse_mode='Markdown'
        )

        state['step'] = USER_STATES['MAIN_MENU']
        await self.callback_handlers.mostrar_menu_principal(update.message)

    def get_handlers(self):
        """Get all message handlers"""
        return [
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_message)
        ]