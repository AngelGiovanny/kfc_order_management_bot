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


class CommandHandlers:
    def __init__(self, callback_handlers=None):
        self.order_service = OrderService()
        self.user_states = {}
        self.user_last_activity = {}
        self.activity_records = {}
        self.callback_handlers = callback_handlers
        self.report_service = ReportService()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command - MEJORADO CON REINICIO COMPLETO"""
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.full_name

        # REINICIAR COMPLETAMENTE el estado del usuario
        self.user_states[user_id] = {'step': 'get_store_code'}
        self.user_last_activity[user_id] = datetime.datetime.now().timestamp()

        # Registrar actividad
        self._registrar_actividad(user_id, username, None, "start")

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

        self._registrar_actividad(user_id, username, None, "reset")

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

        if user_id not in settings.bot.admins:
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
            f"• 📊 Consultas hoy: {len(self.activity_records)}\n"
            f"• 🕐 Tiempo activo: Desde {datetime.datetime.now().strftime('%H:%M')}\n\n"
            f"🔧 *Sistema operativo correctamente*"
        )

        await update.message.reply_text(stats, parse_mode='Markdown')

    # =============================================================================
    # NUEVOS COMANDOS DE REPORTES MEJORADOS CON GUARDADO AUTOMÁTICO
    # =============================================================================

    async def reporte_avanzado(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Nuevo comando para reportes avanzados con gráficas y análisis completo"""
        user_id = update.effective_user.id

        if user_id not in settings.bot.admins:
            await update.message.reply_text("⛔ No tiene permisos de administrador para este comando")
            return

        try:
            await update.message.reply_text("📊 Generando reporte avanzado... Esto puede tomar unos segundos.")

            # Generar reporte completo
            report_data = self.report_service.generate_usage_report(self.activity_records)

            if not report_data or not report_data.get('summary'):
                await update.message.reply_text("❌ No hay datos suficientes para generar el reporte")
                return

            # 1. Enviar gráfica de uso (con guardado automático)
            chart_buffer = self.report_service.generate_usage_chart(report_data, save_file=True)
            if chart_buffer.getbuffer().nbytes > 100:
                await update.message.reply_photo(
                    photo=InputFile(chart_buffer, filename="grafica_uso.png"),
                    caption="📈 **Gráficas de Uso del Bot**\n\nAnálisis visual del uso y distribución de actividades"
                )

            # 2. Enviar reporte Excel mejorado (con guardado automático)
            excel_buffer = self.report_service.generate_excel_report(self.activity_records, report_data, save_file=True)
            if excel_buffer.getbuffer().nbytes > 100:
                filename = f"reporte_avanzado_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
                await update.message.reply_document(
                    document=InputFile(excel_buffer, filename=filename),
                    caption="📊 **Reporte Avanzado en Excel**\n\nIncluye múltiples hojas con análisis detallado"
                )

            # 3. Enviar reporte TXT detallado (con guardado automático)
            txt_report = self.report_service.generate_detailed_txt_report(self.activity_records, report_data, save_file=True)
            if txt_report and "Error generando reporte" not in txt_report:
                txt_buffer = io.BytesIO(txt_report.encode('utf-8'))
                filename = f"reporte_detallado_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.txt"
                await update.message.reply_document(
                    document=InputFile(txt_buffer, filename=filename),
                    caption="📋 **Reporte Detallado en TXT**\n\nResumen ejecutivo y análisis textual"
                )

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
                "`reportes/año/mes/día/`",
                "",
                "🎯 **Usa /estadisticas_detalladas para ver más análisis**"
            ]

            await update.message.reply_text("\n".join(response))

        except Exception as e:
            logger.error(f"Error en reporte avanzado: {str(e)}")
            await update.message.reply_text("❌ Error generando reportes avanzados. Revisa los logs.")

    async def estadisticas_detalladas(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Estadísticas detalladas en el chat con análisis avanzado"""
        user_id = update.effective_user.id

        if user_id not in settings.bot.admins:
            await update.message.reply_text("⛔ No tiene permisos de administrador para este comando")
            return

        try:
            report_data = self.report_service.generate_usage_report(self.activity_records)

            if not report_data or not report_data.get('summary'):
                await update.message.reply_text("📊 No hay datos suficientes para el análisis")
                return

            summary = report_data['summary']
            action_breakdown = report_data.get('action_breakdown', {})
            top_stores = report_data.get('top_stores', {})
            hourly_usage = report_data.get('hourly_usage', {})

            # Calcular métricas adicionales
            total_actions = sum(action_breakdown.values())
            peak_hour = max(hourly_usage.items(), key=lambda x: x[1])[0] if hourly_usage else "N/A"

            response = [
                "📊 **ESTADÍSTICAS DETALLADAS - KFC BOT**",
                "",
                "📈 **RESUMEN EJECUTIVO**",
                f"• Usuarios únicos: {summary['total_users']}",
                f"• Total actividades: {summary['total_activities']}",
                f"• Promedio por usuario: {summary['avg_activities_per_user']:.1f}",
                f"• Hora pico: {peak_hour}:00",
                "",
                "🎯 **DISTRIBUCIÓN POR ACCIÓN**"
            ]

            # Agregar tipos de acción con porcentajes
            for action, count in sorted(action_breakdown.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total_actions) * 100 if total_actions > 0 else 0
                emoji = {
                    'store_access': '🏪',
                    'check_status': '📦',
                    'audit': '📋',
                    'reprint': '🖨️',
                    'generate_image': '🖼️',
                    'comanda': '🍔',
                    'associated_code': '🔗',
                    'start': '🚀'
                }.get(action, '📊')

                action_name = {
                    'store_access': 'Acceso a tienda',
                    'check_status': 'Consulta estado',
                    'audit': 'Auditoría',
                    'reprint': 'Re-impresión',
                    'generate_image': 'Imagen factura',
                    'comanda': 'Comanda',
                    'associated_code': 'Código asociado',
                    'start': 'Inicio sesión'
                }.get(action, action)

                response.append(f"{emoji} {action_name}: {count} ({percentage:.1f}%)")

            # Top tiendas si hay datos
            if top_stores:
                response.extend(["", "🏪 **TOP 5 TIENDAS MÁS ACTIVAS**"])
                for i, (store, count) in enumerate(list(top_stores.items())[:5], 1):
                    response.append(f"{i}. {store}: {count} actividades")

            # Uso por hora si hay datos
            if len(hourly_usage) > 5:
                response.extend(["", "🕐 **HORARIOS MÁS ACTIVOS**"])
                top_hours = sorted(hourly_usage.items(), key=lambda x: x[1], reverse=True)[:3]
                for hour, count in top_hours:
                    response.append(f"• {hour:02d}:00 - {count} actividades")

            response.extend([
                "",
                f"📅 **Reporte generado:** {summary['report_generated_at']}",
                "",
                "💾 **Los reportes completos se guardan automáticamente en:**",
                "`reportes/año/mes/día/`",
                "",
                "💡 **Usa /reporte_avanzado para reportes completos en Excel**"
            ])

            await update.message.reply_text("\n".join(response))

        except Exception as e:
            logger.error(f"Error en estadísticas detalladas: {str(e)}")
            await update.message.reply_text("❌ Error generando estadísticas detalladas")

    async def reporte_diario(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Reporte rápido del día actual con guardado automático"""
        user_id = update.effective_user.id

        if user_id not in settings.bot.admins:
            await update.message.reply_text("⛔ No tiene permisos de administrador para este comando")
            return

        try:
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            today_activities = []

            for user_id, records in self.activity_records.items():
                for record in records:
                    if today in record:
                        today_activities.append(record)

            if not today_activities:
                await update.message.reply_text(f"📊 No hay actividades registradas para hoy ({today})")
                return

            # Análisis simple del día
            users_today = set()
            stores_today = set()
            action_counts = defaultdict(int)

            for activity in today_activities:
                parts = activity.split(' - ')
                if len(parts) >= 2:
                    user_part = parts[1]
                    # Extraer user ID
                    if 'Usuario:' in user_part and '(ID:' in user_part:
                        user_id = user_part.split('(ID: ')[1].split(')')[0]
                        users_today.add(user_id)

                    # Contar acciones
                    if 'Tienda:' in activity:
                        action_counts['Acceso Tienda'] += 1
                        store_part = activity.split('Tienda: ')[1]
                        store_code = store_part.split()[0] if ' ' in store_part else store_part
                        stores_today.add(store_code)
                    elif 'estado' in activity.lower():
                        action_counts['Consulta Estado'] += 1
                    elif 'auditoria' in activity.lower():
                        action_counts['Auditoría'] += 1
                    elif 'reimpresion' in activity.lower():
                        action_counts['Re-impresión'] += 1

            response = [
                f"📊 **REPORTE DIARIO - {today}**",
                "",
                f"👥 **Usuarios activos hoy:** {len(users_today)}",
                f"🏪 **Tiendas activas hoy:** {len(stores_today)}",
                f"📈 **Total actividades hoy:** {len(today_activities)}",
                "",
                "🎯 **DISTRIBUCIÓN DE ACTIVIDADES:**"
            ]

            for action, count in sorted(action_counts.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / len(today_activities)) * 100
                response.append(f"• {action}: {count} ({percentage:.1f}%)")

            if stores_today:
                response.extend(["", "🏪 **TIENDAS ACTIVAS HOY:**"])
                for store in sorted(list(stores_today)[:10]):
                    response.append(f"• {store}")

            response.extend([
                "",
                f"⏰ **Generado:** {datetime.datetime.now().strftime('%H:%M:%S')}",
                "",
                "💾 **Los reportes completos se guardan automáticamente en:**",
                "`reportes/año/mes/día/`",
                "",
                "💡 **Usa /reporte_avanzado para análisis completo con gráficas**"
            ])

            await update.message.reply_text("\n".join(response))

            # Generar y guardar automáticamente el reporte completo del día
            report_data = self.report_service.generate_usage_report(self.activity_records)
            if report_data:
                self.report_service.generate_daily_auto_report(self.activity_records)
                logger.info(f"✅ Reporte diario automático guardado para {today}")

        except Exception as e:
            logger.error(f"Error en reporte diario: {str(e)}")
            await update.message.reply_text("❌ Error generando reporte diario")

    async def reporte_automatico(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Genera y guarda automáticamente reporte sin enviar por Telegram"""
        user_id = update.effective_user.id

        if user_id not in settings.bot.admins:
            await update.message.reply_text("⛔ No tiene permisos de administrador para este comando")
            return

        try:
            await update.message.reply_text("🤖 Generando reporte automático...")

            # Generar y guardar automáticamente sin enviar archivos
            report_data = self.report_service.generate_daily_auto_report(self.activity_records)

            if report_data:
                await update.message.reply_text(
                    "✅ **Reporte automático guardado correctamente**\n\n"
                    f"📊 **Resumen:**\n"
                    f"• 👥 Usuarios: {report_data['summary']['total_users']}\n"
                    f"• 📈 Actividades: {report_data['summary']['total_activities']}\n"
                    f"• 💾 Guardado en: `reportes/{datetime.datetime.now().year}/"
                    f"{datetime.datetime.now().month:02d}/{datetime.datetime.now().day:02d}/`"
                )
            else:
                await update.message.reply_text("❌ No se pudo generar el reporte automático")

        except Exception as e:
            logger.error(f"Error en reporte automático: {str(e)}")
            await update.message.reply_text("❌ Error generando reporte automático")

    def _registrar_actividad(self, user_id: int, username: str, store_code: str = None, action_type: str = None):
        """Registrar actividad del usuario"""
        fecha_hora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        registro = f"{fecha_hora} - Usuario: {username} (ID: {user_id})"

        if store_code:
            registro += f" - Tienda: {store_code}"

        if action_type:
            registro += f" - Acción: {action_type}"

        if user_id not in self.activity_records:
            self.activity_records[user_id] = []

        self.activity_records[user_id].append(registro)

    def get_handlers(self):
        """Get all command handlers"""
        return [
            CommandHandler("start", self.start),
            CommandHandler("reset", self.reset),
            CommandHandler("reporte_conexiones", self.reporte_conexiones),
            CommandHandler("estadisticas", self.estadisticas),
            # NUEVOS COMANDOS DE REPORTES
            CommandHandler("reporte_avanzado", self.reporte_avanzado),
            CommandHandler("estadisticas_detalladas", self.estadisticas_detalladas),
            CommandHandler("reporte_diario", self.reporte_diario),
            CommandHandler("reporte_automatico", self.reporte_automatico),  # Nuevo comando
        ]