from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from src.config.constants import USER_STATES
from src.utils.logger import logger


class CallbackHandlers:
    def __init__(self):
        self.user_states = {}
        self.user_last_activity = {}
        self.conteo_impresiones = {}

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards - COMPLETO Y CORREGIDO"""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        state = self.user_states.get(user_id, {})

        try:
            logger.info(f"📨 Callback recibido: {query.data} de usuario {user_id}")

            # BOTONES DE NAVEGACIÓN
            if query.data == 'volver_menu':
                state['step'] = USER_STATES['MAIN_MENU']
                await self.mostrar_menu_principal(query.message)
                return

            elif query.data == 'finalizar_consulta':
                state['step'] = USER_STATES['GET_STORE_CODE']
                await query.edit_message_text(
                    "✅ *Consulta finalizada* 🎉\n\n"
                    "✨ ¡Gracias por usar el sistema!\n\n"
                    "🔄 Para comenzar una nueva consulta, usa /start o ingresa el código de tienda:",
                    parse_mode='Markdown'
                )
                return

            elif query.data == 'volver_atras':
                await self._handle_volver_atras(query, state)
                return

            # OPCIONES PRINCIPALES DEL MENÚ
            elif query.data == '1':  # Verificar estado de ordenes
                await self._handle_opcion_1(query, state)

            elif query.data == '2':  # Auditoría
                await self._handle_opcion_2(query, state)

            elif query.data == '3':  # Imagen Factura
                await self._handle_opcion_3(query, state)

            elif query.data == '4':  # Ver Comanda
                await self._handle_opcion_4(query, state)

            elif query.data == '5':  # Código Asociado - ¡CORREGIDO!
                await self._handle_opcion_5(query, state)

            elif query.data == '7':  # Re-Impresion
                await self._handle_opcion_7(query, state)

            elif query.data == '8':  # Cambiar Tienda
                await self._handle_opcion_8(query, state)

            # SUBMENÚ DE RE-IMPRESIONES
            elif query.data in ['factura', 'nota_credito', 'comanda']:
                await self._handle_reprint_submenu(query, state)

            else:
                logger.warning(f"❌ Callback no reconocido: {query.data}")
                await query.edit_message_text(
                    "❌ *Opción no reconocida*\n\n"
                    "🔄 Por favor, usa /start para reiniciar.",
                    parse_mode='Markdown'
                )
                return

            self.user_states[user_id] = state

        except Exception as e:
            logger.error(f"❌ Error handling callback: {str(e)}")
            await query.edit_message_text(
                "❌ *Error procesando solicitud*\n\n"
                "🔄 Por favor, intenta nuevamente o usa /start para reiniciar.",
                parse_mode='Markdown'
            )

    async def _handle_opcion_1(self, query, state):
        """Verificar Estado de Orden"""
        state['step'] = USER_STATES['GET_ORDER_STATUS']
        keyboard = [
            [InlineKeyboardButton("↩️ Volver al Menú", callback_data='volver_menu')],
            [InlineKeyboardButton("❌ Finalizar", callback_data='finalizar_consulta')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text="🔍 *Verificar Estado de Orden*\n\n"
                 "📝 **Por favor, ingresa el número de orden:**\n"
                 "(Ejemplo: APP123456789)\n\n"
                 "💡 *También puedes usar los botones de navegación*",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def _handle_opcion_2(self, query, state):
        """Auditoría de Orden"""
        state['step'] = USER_STATES['GET_ORDER_AUDIT']
        keyboard = [
            [InlineKeyboardButton("↩️ Volver al Menú", callback_data='volver_menu')],
            [InlineKeyboardButton("❌ Finalizar", callback_data='finalizar_consulta')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text="📊 *Auditoría de Orden*\n\n"
                 "📝 **Por favor, ingresa el número de orden:**\n"
                 "(Ejemplo: APP123456789)\n\n"
                 "📋 *Obtendrás el historial completo de la orden*",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def _handle_opcion_3(self, query, state):
        """Imagen de Factura"""
        state['step'] = USER_STATES['GET_INVOICE_ID']
        keyboard = [
            [InlineKeyboardButton("↩️ Volver al Menú", callback_data='volver_menu')],
            [InlineKeyboardButton("❌ Finalizar", callback_data='finalizar_consulta')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text="🧾 *Generar Imagen de Factura*\n\n"
                 "🔢 **Por favor, ingresa el ID de la factura:**\n"
                 "(Ejemplo: K100F001657227)\n\n"
                 "🖼️ *Se generará una imagen de la factura*",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def _handle_opcion_4(self, query, state):
        """Ver Comanda"""
        state['step'] = USER_STATES['GET_COMANDA_ID']
        keyboard = [
            [InlineKeyboardButton("↩️ Volver al Menú", callback_data='volver_menu')],
            [InlineKeyboardButton("❌ Finalizar", callback_data='finalizar_consulta')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text="📦 *Ver Comanda*\n\n"
                 "🔢 **Por favor, ingresa el ID de la comanda:**\n"
                 "(Ejemplo: K100F001657227)\n\n"
                 "🖼️ *Se mostrará la imagen de la comanda*",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def _handle_opcion_5(self, query, state):
        """Código Asociado - ¡IMPLEMENTADO CORRECTAMENTE!"""
        state['step'] = USER_STATES['GET_CFAC_ID']
        keyboard = [
            [InlineKeyboardButton("↩️ Volver al Menú", callback_data='volver_menu')],
            [InlineKeyboardButton("❌ Finalizar", callback_data='finalizar_consulta')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text="🔍 *Buscar Código Asociado*\n\n"
                 "🧾 **Por favor, ingresa el ID de la factura:**\n"
                 "(Ejemplo: K100F001657227)\n\n"
                 "🔗 *Obtendrás el código asociado de la factura*",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def _handle_opcion_7(self, query, state):
        """Re-Impresión"""
        state['step'] = USER_STATES['SUBREPRINT_MENU']
        await self.mostrar_menu_reimpresion(query.message)

    async def _handle_opcion_8(self, query, state):
        """Cambiar Tienda"""
        state['step'] = USER_STATES['GET_STORE_CODE']
        await query.edit_message_text(
            text="🔄 *Cambiar Tienda*\n\n"
                 "🏪 **Por favor, ingresa el nuevo código de tienda:**\n"
                 "(Ejemplo: K002, K080, K100)\n\n"
                 "💡 *También puedes usar /start para reiniciar completamente*",
            parse_mode='Markdown'
        )

    async def _handle_reprint_submenu(self, query, state):
        """Manejar submenú de re-impresiones"""
        state['step'] = USER_STATES['GET_REPRINT_ID']
        state['reimpresion_id_type'] = query.data
        document_name = {
            'factura': 'factura 🧾',
            'nota_credito': 'nota de crédito 📄',
            'comanda': 'comanda 📦'
        }[query.data]

        keyboard = [
            [InlineKeyboardButton("↩️ Volver Atrás", callback_data='volver_atras')],
            [InlineKeyboardButton("🏠 Menú Principal", callback_data='volver_menu')],
            [InlineKeyboardButton("❌ Finalizar", callback_data='finalizar_consulta')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text=f"🖨️ *Re-Impresión de {document_name}*\n\n"
                 f"🔢 **Por favor, ingresa el ID del documento:**\n"
                 f"(Ejemplo: K100F001657227)\n\n"
                 f"💡 *Usa los botones para navegar*",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def _handle_volver_atras(self, query, state):
        """Manejar la acción de volver atrás"""
        user_id = query.from_user.id

        # Lógica para determinar a dónde volver basado en el estado actual
        if state.get('step') == USER_STATES['GET_REPRINT_ID']:
            state['step'] = USER_STATES['SUBREPRINT_MENU']
            await self.mostrar_menu_reimpresion(query.message)
        elif state.get('step') in [USER_STATES['GET_ORDER_STATUS'], USER_STATES['GET_ORDER_AUDIT'],
                                   USER_STATES['GET_INVOICE_ID'], USER_STATES['GET_COMANDA_ID'],
                                   USER_STATES['GET_CFAC_ID']]:
            state['step'] = USER_STATES['MAIN_MENU']
            await self.mostrar_menu_principal(query.message)
        else:
            # Por defecto, volver al menú principal
            state['step'] = USER_STATES['MAIN_MENU']
            await self.mostrar_menu_principal(query.message)

    async def mostrar_menu_principal(self, message):
        """Show main menu - MEJORADO CON BOTONES DE NAVEGACIÓN"""
        store_code = self.user_states.get(message.chat.id, {}).get('store_code', 'No seleccionada')
        username = message.chat.first_name or 'Usuario'

        keyboard = [
            [
                InlineKeyboardButton("📋 Verificar Orden", callback_data='1'),
                InlineKeyboardButton("📊 Auditoría", callback_data='2')
            ],
            [
                InlineKeyboardButton("🧾 Imagen Factura", callback_data='3'),
                InlineKeyboardButton("📦 Ver Comanda", callback_data='4')
            ],
            [
                InlineKeyboardButton("🔍 Código Asociado", callback_data='5')
            ],
            [
                InlineKeyboardButton("🖨️ Re-Impresión", callback_data='7')
            ],
            [
                InlineKeyboardButton("🔄 Cambiar Tienda", callback_data='8'),
                InlineKeyboardButton("❌ Finalizar", callback_data='finalizar_consulta')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        menu_message = (
            "🎯 *Menú Principal* 🍗\n\n"
            f"🏪 **Tienda activa:** `{store_code}`\n"
            f"👤 **Usuario:** {username}\n\n"
            "📋 *Selecciona una opción:*\n\n"
            "💡 **Navegación:**\n"
            "• Usa /start para reiniciar completamente\n"
            "• Usa /reset para cambiar de tienda\n"
            "• Usa los botones para navegar"
        )

        await message.reply_text(
            menu_message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def mostrar_menu_reimpresion(self, message):
        """Show reprint menu - MEJORADO CON BOTONES DE NAVEGACIÓN"""
        keyboard = [
            [InlineKeyboardButton("🧾 Factura", callback_data='factura')],
            [InlineKeyboardButton("📄 Nota Crédito", callback_data='nota_credito')],
            [InlineKeyboardButton("📦 Comanda", callback_data='comanda')],
            [
                InlineKeyboardButton("↩️ Volver al Menú", callback_data='volver_menu'),
                InlineKeyboardButton("❌ Finalizar", callback_data='finalizar_consulta')
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        reprint_message = (
            "🖨️ *Re-Impresión de Documentos*\n\n"
            "📋 *Selecciona el tipo de documento:*\n\n"
            "💡 **Límites de re-impresión:**\n"
            "• 🧾 Factura: 1 vez\n"
            "• 📄 Nota Crédito: 1 vez\n"
            "• 📦 Comanda: 2 veces\n\n"
            "🔧 **Navegación disponible con los botones**"
        )

        await message.reply_text(
            reprint_message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    def get_handlers(self):
        """Get all callback handlers"""
        return [
            CallbackQueryHandler(self.handle_callback)
        ]