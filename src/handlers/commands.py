from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler
import datetime

from src.config.settings import settings
from src.utils.logger import logger
from src.services.order_service import OrderService


class CommandHandlers:
    def __init__(self, callback_handlers=None):
        self.order_service = OrderService()
        self.user_states = {}
        self.user_last_activity = {}
        self.activity_records = {}
        self.callback_handlers = callback_handlers

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command - MEJORADO CON REINICIO COMPLETO"""
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.full_name

        # REINICIAR COMPLETAMENTE el estado del usuario
        self.user_states[user_id] = {'step': 'get_store_code'}
        self.user_last_activity[user_id] = datetime.datetime.now().timestamp()

        # Log connection
        logger.log_connection(user_id, username, None, "start")

        welcome_message = (
            "🔄 *¡Reiniciando Sistema!* 🔄\n\n"
            "🎉 *¡Bienvenido al Sistema KFC!* 🍗\n\n"
            "🌟 *Gestión Inteligente de Órdenes*\n"
            "----------------------------------------\n\n"
            "📋 **¿Qué puedes hacer?**\n"
            "• ✅ Verificar estado de órdenes\n"
            "• 📊 Auditoría completa\n"
            "• 🧾 Generar imágenes de facturas\n"
            "• 🖨️ Re-impresiones inteligentes\n"
            "• 📦 Seguimiento de comandas\n\n"
            "🔢 **Por favor, ingresa el código de tu tienda:**\n"
            "*(Ejemplo: K002, K080, K100, K101)*"
        )

        await update.message.reply_text(
            welcome_message,
            parse_mode='Markdown',
            reply_markup=None
        )

    async def reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Nuevo comando /reset para reiniciar completamente"""
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.full_name

        # LIMPIAR COMPLETAMENTE el estado
        self.user_states[user_id] = {'step': 'get_store_code'}
        self.user_last_activity[user_id] = datetime.datetime.now().timestamp()

        logger.log_connection(user_id, username, None, "reset")

        reset_message = (
            "🔄 *¡Sistema Reiniciado!* 🔄\n\n"
            "✨ Todos los datos anteriores han sido limpiados.\n\n"
            "🔢 **Por favor, ingresa el código de tu tienda:**\n"
            "*(Ejemplo: K002, K080, K100, K101)*"
        )

        await update.message.reply_text(
            reset_message,
            parse_mode='Markdown'
        )

    async def reporte_conexiones(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Reporte de conexiones activas"""
        user_id = update.effective_user.id

        if user_id not in settings.bot.admin_users:
            await update.message.reply_text("❌ No tienes permisos para esta acción.")
            return

        active_connections = len([state for state in self.user_states.values()
                                  if state.get('store_code')])

        reporte = (
            f"📊 *Reporte de Conexiones*\n\n"
            f"• 👥 Usuarios activos: {len(self.user_states)}\n"
            f"• 🔗 Conexiones a tiendas: {active_connections}\n"
            f"• ⏰ Última actividad: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"📋 *Usuarios conectados:*\n"
        )

        for uid, state in self.user_states.items():
            if state.get('store_code'):
                last_activity = datetime.datetime.fromtimestamp(
                    self.user_last_activity.get(uid, 0)
                ).strftime('%H:%M:%S')
                reporte += f"• 🏪 {state.get('store_code')} - ⏰ {last_activity}\n"

        await update.message.reply_text(reporte, parse_mode='Markdown')

    async def estadisticas(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Estadísticas del sistema"""
        user_id = update.effective_user.id

        if user_id not in settings.bot.admin_users:
            await update.message.reply_text("❌ No tienes permisos para esta acción.")
            return

        stats = (
            f"📈 *Estadísticas del Sistema*\n\n"
            f"• 🤖 Bot iniciado: Sí\n"
            f"• 👥 Usuarios registrados: {len(self.user_states)}\n"
            f"• 🏪 Tiendas activas: {len(set(state.get('store_code') for state in self.user_states.values() if state.get('store_code')))}\n"
            f"• 📊 Consultas hoy: {len(self.activity_records)}\n"
            f"• 🕐 Tiempo activo: Desde {datetime.datetime.now().strftime('%H:%M')}\n\n"
            f"🔧 *Sistema operativo correctamente*"
        )

        await update.message.reply_text(stats, parse_mode='Markdown')

    def get_handlers(self):
        """Get all command handlers"""
        return [
            CommandHandler("start", self.start),
            CommandHandler("reset", self.reset),
            CommandHandler("reporte_conexiones", self.reporte_conexiones),
            CommandHandler("estadisticas", self.estadisticas),
        ]