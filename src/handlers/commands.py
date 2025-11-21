import io
import datetime
from datetime import timedelta
from collections import defaultdict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ContextTypes, CommandHandler

from src.config.settings import settings
from src.utils.logger import logger
from src.services.order_service import OrderService
from src.services.report_service import ReportService
from src.services.reimpresion_service import ReimpresionService


class CommandHandlers:
    def __init__(self, callback_handlers=None):
        self.order_service = OrderService()
        self.user_states = {}
        self.user_last_activity = {}
        self.activity_records = {}
        self.callback_handlers = callback_handlers
        self.report_service = ReportService()
        self.reimpresion_service = ReimpresionService()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        try:
            user_id = update.effective_user.id
            username = update.effective_user.username or update.effective_user.full_name

            # Reiniciar estado del usuario
            self.user_states[user_id] = {'step': 'get_store_code'}
            self.user_last_activity[user_id] = datetime.datetime.now().timestamp()

            # Registrar actividad
            self._registrar_actividad(user_id, username, None, "start")

            welcome_message = (
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
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Error en comando start: {str(e)}")
            await update.message.reply_text(
                "❌ Error al iniciar el sistema. Por favor, intenta nuevamente."
            )

    async def reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /reset para reiniciar completamente"""
        try:
            user_id = update.effective_user.id
            username = update.effective_user.username or update.effective_user.full_name

            # Limpiar estado
            self.user_states[user_id] = {'step': 'get_store_code'}
            self.user_last_activity[user_id] = datetime.datetime.now().timestamp()

            self._registrar_actividad(user_id, username, None, "reset")

            await update.message.reply_text(
                "🔄 *¡Sistema Reiniciado!*\n\n"
                "🔢 **Ingresa el código de tienda:**\n"
                "(Ejemplo: K002, K080, K100)",
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Error en comando reset: {str(e)}")
            await update.message.reply_text("❌ Error al reiniciar el sistema.")

    async def handle_reimprimir(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejar comando de reimpresión /reimprimir"""
        try:
            # Verificar parámetros
            if not context.args or len(context.args) < 2:
                await update.message.reply_text(
                    "❌ *Formato incorrecto*\n\n"
                    "📋 **Uso:** `/reimprimir <cfac_id> <tipo_documento>`\n\n"
                    "🎯 **Ejemplos:**\n"
                    "• `/reimprimir F001-123456 factura`\n"
                    "• `/reimprimir NC001-789012 nota_credito`\n"
                    "• `/reimprimir C001-345678 comanda`\n\n"
                    "📄 **Tipos:** `factura`, `nota_credito`, `comanda`",
                    parse_mode='Markdown'
                )
                return

            cfac_id = context.args[0]
            tipo_documento = context.args[1].lower()

            # Validar tipo de documento
            if tipo_documento not in ['factura', 'nota_credito', 'comanda']:
                await update.message.reply_text(
                    "❌ *Tipo de documento no válido*\n\n"
                    "📋 **Tipos permitidos:**\n"
                    "• `factura`\n• `nota_credito`\n• `comanda`",
                    parse_mode='Markdown'
                )
                return

            # Mensaje de procesamiento
            processing_msg = await update.message.reply_text(
                f"🔄 *Procesando reimpresión...*\n\n"
                f"📄 **Documento:** {cfac_id}\n"
                f"📋 **Tipo:** {tipo_documento}\n"
                f"⏳ *Por favor espere...*",
                parse_mode='Markdown'
            )

            # Ejecutar reimpresión
            resultado = self.reimpresion_service.reimprimir_documento(cfac_id, tipo_documento)

            # Enviar resultado
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
                error_msg = (
                    f"❌ *Error en impresión*\n\n"
                    f"📄 **Documento:** `{cfac_id}`\n"
                    f"⚠️ **Error:** {resultado.get('error', 'Desconocido')}"
                )

                if resultado.get('requires_support'):
                    error_msg += "\n\n🚨 **CONTACTE CON SOPORTE TÉCNICO**"

                await processing_msg.edit_text(error_msg, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Error en comando reimprimir: {str(e)}")
            await update.message.reply_text(
                f"❌ Error procesando comando: {str(e)}"
            )

    async def reporte_conexiones(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Reporte de conexiones activas"""
        user_id = update.effective_user.id

        if user_id not in settings.bot.admins:
            await update.message.reply_text("❌ No tienes permisos para esta acción.")
            return

        active_connections = len([state for state in self.user_states.values()
                                  if state.get('store_code')])

        reporte = (
            f"📊 *Reporte de Conexiones*\n\n"
            f"• 👥 Usuarios activos: {len(self.user_states)}\n"
            f"• 🔗 Conexiones a tiendas: {active_connections}\n"
            f"• ⏰ Última actividad: {datetime.datetime.now().strftime('%H:%M:%S')}"
        )

        await update.message.reply_text(reporte, parse_mode='Markdown')

    async def estadisticas(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Estadísticas básicas del sistema"""
        user_id = update.effective_user.id

        if user_id not in settings.bot.admins:
            await update.message.reply_text("❌ No tienes permisos para esta acción.")
            return

        stats = (
            f"📈 *Estadísticas del Sistema*\n\n"
            f"• 🤖 Bot iniciado: Sí\n"
            f"• 👥 Usuarios registrados: {len(self.user_states)}\n"
            f"• 🏪 Tiendas activas: {len(set(state.get('store_code') for state in self.user_states.values() if state.get('store_code')))}\n"
            f"• 📊 Consultas hoy: {len(self.activity_records)}"
        )

        await update.message.reply_text(stats, parse_mode='Markdown')

    async def reporte_avanzado(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Nuevo comando para reportes avanzados con gráficas y análisis completo - CORREGIDO"""
        user_id = update.effective_user.id

        if user_id not in settings.bot.admins:
            await update.message.reply_text("⛔ No tiene permisos de administrador para este comando")
            return

        try:
            processing_msg = await update.message.reply_text(
                "📊 *Generando reporte avanzado...*\n\n"
                "⏳ *Esto puede tomar unos segundos...*",
                parse_mode='Markdown'
            )

            # Generar reporte completo
            report_data = self.report_service.generate_usage_report(self.activity_records)

            if not report_data or report_data['summary']['total_activities'] == 0:
                await processing_msg.edit_text(
                    "📊 *No hay datos suficientes para generar el reporte*\n\n"
                    "💡 *Realiza algunas actividades en el bot primero.*",
                    parse_mode='Markdown'
                )
                return

            # 1. Enviar gráfica de uso
            try:
                chart_buffer = self.report_service.generate_usage_chart(report_data, save_file=True)
                if chart_buffer.getbuffer().nbytes > 1000:  # Verificar que no esté vacío
                    await update.message.reply_photo(
                        photo=InputFile(chart_buffer, filename="grafica_uso.png"),
                        caption="📈 **Gráficas de Uso del Bot**\n\nAnálisis visual del uso y distribución de actividades",
                        parse_mode='Markdown'
                    )
            except Exception as e:
                logger.error(f"Error enviando gráfica: {str(e)}")
                await update.message.reply_text("❌ Error generando gráficas")

            # 2. Enviar reporte Excel
            try:
                excel_buffer = self.report_service.generate_excel_report(self.activity_records, report_data,
                                                                         save_file=True)
                if excel_buffer.getbuffer().nbytes > 1000:
                    filename = f"reporte_avanzado_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
                    await update.message.reply_document(
                        document=InputFile(excel_buffer, filename=filename),
                        caption="📊 **Reporte Avanzado en Excel**\n\nIncluye múltiples hojas con análisis detallado",
                        parse_mode='Markdown'
                    )
            except Exception as e:
                logger.error(f"Error enviando Excel: {str(e)}")
                await update.message.reply_text("❌ Error generando reporte Excel")

            # 3. Enviar reporte TXT
            try:
                txt_report = self.report_service.generate_detailed_txt_report(self.activity_records, report_data,
                                                                              save_file=True)
                if txt_report and "Error generando reporte" not in txt_report:
                    txt_buffer = io.BytesIO(txt_report.encode('utf-8'))
                    filename = f"reporte_detallado_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.txt"
                    await update.message.reply_document(
                        document=InputFile(txt_buffer, filename=filename),
                        caption="📋 **Reporte Detallado en TXT**\n\nResumen ejecutivo y análisis textual",
                        parse_mode='Markdown'
                    )
            except Exception as e:
                logger.error(f"Error enviando TXT: {str(e)}")

            # 4. Resumen rápido en el chat
            summary = report_data['summary']
            response = [
                "✅ **REPORTE COMPLETO GENERADO**",
                "",
                f"📅 **Período analizado:** {summary.get('analysis_period_days', 'N/A')} días",
                f"👥 **Usuarios únicos:** {summary['total_users']}",
                f"📈 **Total actividades:** {summary['total_activities']}",
                f"📊 **Promedio por usuario:** {summary['avg_activities_per_user']:.1f}",
                "",
                "💾 **Todos los archivos se han guardado automáticamente en:**",
                "`C:/ChatBot/Logs/reportes/año/mes/día/`",
                "",
                "🎯 **Usa /estadisticas_detalladas para ver más análisis**"
            ]

            await processing_msg.edit_text("\n".join(response), parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Error en reporte avanzado: {str(e)}")
            await update.message.reply_text(
                "❌ *Error generando reportes avanzados*\n\n"
                f"📋 **Detalles:** `{str(e)}`",
                parse_mode='Markdown'
            )
    async def estadisticas_detalladas(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Estadísticas detalladas"""
        user_id = update.effective_user.id

        if user_id not in settings.bot.admins:
            await update.message.reply_text("⛔ No tiene permisos para este comando")
            return

        try:
            report_data = self.report_service.generate_usage_report(self.activity_records)

            if not report_data or not report_data.get('summary'):
                await update.message.reply_text("📊 No hay datos para el análisis")
                return

            summary = report_data['summary']
            response = [
                "📊 **ESTADÍSTICAS DETALLADAS**",
                f"👥 Usuarios únicos: {summary['total_users']}",
                f"📈 Total actividades: {summary['total_activities']}",
                f"📊 Promedio por usuario: {summary['avg_activities_per_user']:.1f}",
            ]

            await update.message.reply_text("\n".join(response))

        except Exception as e:
            logger.error(f"Error en estadísticas: {str(e)}")
            await update.message.reply_text("❌ Error generando estadísticas")

    async def reporte_diario(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Reporte del día actual"""
        user_id = update.effective_user.id

        if user_id not in settings.bot.admins:
            await update.message.reply_text("⛔ No tiene permisos para este comando")
            return

        try:
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            today_activities = []

            for user_id, records in self.activity_records.items():
                for record in records:
                    if today in record:
                        today_activities.append(record)

            if not today_activities:
                await update.message.reply_text(f"📊 No hay actividades para hoy ({today})")
                return

            response = [
                f"📊 **REPORTE DIARIO - {today}**",
                f"📈 Total actividades hoy: {len(today_activities)}",
                f"⏰ Generado: {datetime.datetime.now().strftime('%H:%M:%S')}",
            ]

            await update.message.reply_text("\n".join(response))

        except Exception as e:
            logger.error(f"Error en reporte diario: {str(e)}")
            await update.message.reply_text("❌ Error generando reporte diario")

    async def reporte_automatico(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Reporte automático"""
        user_id = update.effective_user.id

        if user_id not in settings.bot.admins:
            await update.message.reply_text("⛔ No tiene permisos para este comando")
            return

        try:
            await update.message.reply_text("🤖 Generando reporte automático...")
            report_data = self.report_service.generate_daily_auto_report(self.activity_records)

            if report_data:
                await update.message.reply_text("✅ Reporte automático guardado")
            else:
                await update.message.reply_text("❌ No se pudo generar el reporte")

        except Exception as e:
            logger.error(f"Error en reporte automático: {str(e)}")
            await update.message.reply_text("❌ Error generando reporte automático")

    def _registrar_actividad(self, user_id: int, username: str, store_code: str = None, action_type: str = None):
        """Registrar actividad del usuario"""
        try:
            fecha_hora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            registro = f"{fecha_hora} - Usuario: {username} (ID: {user_id})"

            if store_code:
                registro += f" - Tienda: {store_code}"

            if action_type:
                registro += f" - Acción: {action_type}"

            if user_id not in self.activity_records:
                self.activity_records[user_id] = []

            self.activity_records[user_id].append(registro)
        except Exception as e:
            logger.error(f"Error registrando actividad: {str(e)}")

    def get_handlers(self):
        """Get all command handlers"""
        return [
            CommandHandler("start", self.start),
            CommandHandler("reset", self.reset),
            CommandHandler("reimprimir", self.handle_reimprimir),
            CommandHandler("reporte_conexiones", self.reporte_conexiones),
            CommandHandler("estadisticas", self.estadisticas),
            CommandHandler("reporte_avanzado", self.reporte_avanzado),
            CommandHandler("estadisticas_detalladas", self.estadisticas_detalladas),
            CommandHandler("reporte_diario", self.reporte_diario),
            CommandHandler("reporte_automatico", self.reporte_automatico),
        ]