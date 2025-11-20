import asyncio
import signal
import sys
import os
from telegram.ext import Application

from src.config.settings import settings
from src.utils.logger import logger
from src.handlers.commands import CommandHandlers
from src.handlers.messages import MessageHandlers
from src.handlers.callbacks import CallbackHandlers
from src.services.image_service import image_service
from src.services.report_service import ReportService

class KFCBot:
    def __init__(self):
        self.settings = settings
        self.application = None
        self.callback_handlers = CallbackHandlers()
        self.command_handlers = CommandHandlers()
        self.message_handlers = MessageHandlers(self.callback_handlers)
        self._stop_event = asyncio.Event()

    def setup_handlers(self):
        """Setup all bot handlers"""
        # Add command handlers
        for handler in self.command_handlers.get_handlers():
            self.application.add_handler(handler)

        # Add callback handlers
        for handler in self.callback_handlers.get_handlers():
            self.application.add_handler(handler)

        # Add message handlers
        for handler in self.message_handlers.get_handlers():
            self.application.add_handler(handler)

    def setup_error_handler(self):
        """Setup error handling"""

        async def error_handler(update, context):
            logger.error(f"Exception while handling update: {context.error}")

        self.application.add_error_handler(error_handler)

    async def start(self):
        """Start the bot"""
        try:
            logger.info("Starting KFC Order Management Bot...")

            # Create application
            self.application = (
                Application.builder()
                .token(self.settings.bot.token)
                .build()
            )

            # Setup handlers
            self.setup_handlers()
            self.setup_error_handler()

            # Initialize application
            await self.application.initialize()

            # Start polling with proper shutdown handling
            await self.application.start()

            logger.info("Bot started successfully - Waiting for messages...")

            # Keep the bot running until stop event is set
            await self._stop_event.wait()

        except Exception as e:
            logger.error(f"Failed to start bot: {str(e)}")
            raise

    async def run_polling(self):
        """Run the bot with polling"""
        try:
            await self.application.run_polling(
                drop_pending_updates=True,
                allowed_updates=None,
                stop_signals=None  # We handle signals ourselves
            )
        except Exception as e:
            logger.error(f"Polling error: {str(e)}")
            raise

    async def shutdown(self):
        """Shutdown the bot gracefully"""
        logger.info("Shutting down KFC Bot...")

        try:
            # Signal the stop event
            self._stop_event.set()

            if self.application:
                if self.application.running:
                    await self.application.stop()
                await self.application.shutdown()

        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")

        # Cleanup image service
        image_service.cleanup()

        logger.info("Bot shutdown completed")


def setup_asyncio_event_loop():
    """Setup asyncio event loop for Windows compatibility"""
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop


async def main():
    """Main application entry point"""
    bot = KFCBot()

    try:
        # Start the bot
        await bot.start()

    except KeyboardInterrupt:
        print("\nBot interrupted by user")
    except Exception as e:
        logger.error(f"Bot crashed: {str(e)}")
        print(f"Error: {e}")
    finally:
        # Ensure proper shutdown
        await bot.shutdown()


if __name__ == '__main__':
    # Setup proper event loop
    loop = setup_asyncio_event_loop()

    try:
        # Run the main function
        if loop.is_running():
            # If loop is already running (e.g., in Jupyter)
            task = loop.create_task(main())
            try:
                task.result()
            except Exception as e:
                print(f"Error: {e}")
        else:
            # Standard execution
            loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\nApplication stopped by user")
    finally:
        if not loop.is_closed():
            loop.close()


            async def reporte_avanzado(update: Update, context: CallbackContext) -> None:
                """Nuevo comando para reportes avanzados"""
                user_id = update.message.chat.id
                if user_id in admins:
                    try:
                        await update.message.reply_text("📊 Generando reporte avanzado...")

                        # Generar reporte completo
                        report_data = ReportService.generate_usage_report(activity_records)

                        if not report_data:
                            await update.message.reply_text("❌ Error generando reporte")
                            return

                        # Enviar gráfica
                        chart_buffer = ReportService.generate_usage_chart(report_data)
                        if chart_buffer.getbuffer().nbytes > 0:
                            await update.message.reply_photo(
                                photo=chart_buffer,
                                caption="📈 Gráficas de Uso del Bot"
                            )

                        # Enviar reporte Excel
                        excel_buffer = ReportService.generate_excel_report(activity_records, report_data)
                        await update.message.reply_document(
                            document=InputFile(excel_buffer,
                                               filename=f"reporte_avanzado_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"),
                            caption="📄 Reporte Avanzado en Excel"
                        )

                        # Enviar reporte TXT detallado
                        txt_report = ReportService.generate_detailed_txt_report(activity_records, report_data)
                        txt_buffer = io.BytesIO(txt_report.encode('utf-8'))
                        await update.message.reply_document(
                            document=InputFile(txt_buffer,
                                               filename=f"reporte_detallado_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"),
                            caption="📋 Reporte Detallado en TXT"
                        )

                    except Exception as e:
                        logger.error(f"Error en reporte avanzado: {str(e)}")
                        await update.message.reply_text("❌ Error generando reportes avanzados")
                else:
                    await update.message.reply_text("⛔ No tiene permisos para este comando")


            async def estadisticas_detalladas(update: Update, context: CallbackContext) -> None:
                """Estadísticas detalladas en el chat"""
                user_id = update.message.chat.id
                if user_id in admins:
                    try:
                        report_data = ReportService.generate_usage_report(activity_records)

                        if not report_data:
                            await update.message.reply_text("❌ Error generando estadísticas")
                            return

                        response = [
                            "📊 *ESTADÍSTICAS DETALLADAS*",
                            "",
                            f"👥 *Usuarios Únicos:* {report_data['summary']['total_users']}",
                            f"📈 *Total Actividades:* {report_data['summary']['total_activities']}",
                            f"📊 *Promedio por Usuario:* {report_data['summary']['avg_activities_per_user']:.1f}",
                            "",
                            "*📋 DISTRIBUCIÓN POR ACCIÓN:*"
                        ]

                        for action, count in report_data['action_breakdown'].items():
                            percentage = (count / report_data['summary']['total_activities']) * 100
                            response.append(f"• {action}: {count} ({percentage:.1f}%)")

                        response.extend([
                            "",
                            "*🏪 TOP 5 TIENDAS:*"
                        ])

                        top_stores = list(report_data['top_stores'].items())[:5]
                        for i, (store, count) in enumerate(top_stores, 1):
                            response.append(f"{i}. {store}: {count} actividades")

                        response.extend([
                            "",
                            f"🕐 *Hora Pico:* {max(report_data['hourly_usage'].items(), key=lambda x: x[1])[0]}:00",
                            f"📅 *Reporte generado:* {report_data['summary']['report_generated_at']}"
                        ])

                        await update.message.reply_text("\n".join(response))

                    except Exception as e:
                        logger.error(f"Error en estadísticas detalladas: {str(e)}")
                        await update.message.reply_text("❌ Error generando estadísticas")
                else:
                    await update.message.reply_text("⛔ No tiene permisos para este comando")