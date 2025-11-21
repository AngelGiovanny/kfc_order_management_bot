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

# AGREGAR ESTAS IMPORTACIONES NUEVAS
import win32print
import win32ui


# AGREGAR ESTA CLASE NUEVA PARA MANEJAR IMPRESORAS
class ImpresoraManager:
    def imprimir_ticket(self, contenido, nombre_impresora=None):
        """Envía contenido directamente a la impresora física"""
        try:
            # 1. Obtener nombre de impresora
            if nombre_impresora:
                printer_name = nombre_impresora
            else:
                printer_name = win32print.GetDefaultPrinter()

            print(f"🖨️ Intentando imprimir en: {printer_name}")

            # 2. Conectar a la impresora
            hprinter = win32print.OpenPrinter(printer_name)

            try:
                # 3. Iniciar documento de impresión
                win32print.StartDocPrinter(hprinter, 1, ("Ticket KFC", None, "RAW"))
                win32print.StartPagePrinter(hprinter)

                # 4. Enviar texto a la impresora
                # Agregar saltos de línea para impresora térmica
                contenido_impresora = contenido + "\n\n\n\n\n"  # Saltos para cortar ticket
                win32print.WritePrinter(hprinter, contenido_impresora.encode('utf-8'))

                # 5. Finalizar impresión
                win32print.EndPagePrinter(hprinter)
                win32print.EndDocPrinter(hprinter)

                print(f"✅ Ticket enviado exitosamente a: {printer_name}")
                return True

            except Exception as e:
                print(f"❌ Error durante la impresión: {e}")
                return False
            finally:
                win32print.ClosePrinter(hprinter)

        except Exception as e:
            print(f"❌ Error conectando a la impresora: {e}")
            return False

    def listar_impresoras(self):
        """Lista todas las impresoras disponibles"""
        try:
            impresoras = win32print.EnumPrinters(2)  # 2 = PRINTER_ENUM_LOCAL
            print("\n🖨️ IMPRESORAS DISPONIBLES:")
            for i, impresora in enumerate(impresoras):
                print(f"  {i + 1}. {impresora[2]}")
            return [imp[2] for imp in impresoras]
        except Exception as e:
            print(f"Error listando impresoras: {e}")
            return []


class KFCBot:
    def __init__(self):
        self.settings = settings
        self.application = None
        self.callback_handlers = CallbackHandlers()
        self.command_handlers = CommandHandlers()
        self.message_handlers = MessageHandlers(self.callback_handlers)
        self._stop_event = asyncio.Event()

        # AGREGAR ESTA LÍNEA: Inicializar el manager de impresión
        self.impresora_manager = ImpresoraManager()

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

            # AGREGAR ESTO: Mostrar impresoras disponibles al iniciar
            print("\n" + "=" * 50)
            print("INICIANDO SISTEMA DE IMPRESIÓN KFC")
            print("=" * 50)
            self.impresora_manager.listar_impresoras()
            print("=" * 50)

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

    # AGREGAR ESTE MÉTODO NUEVO para imprimir órdenes
    def imprimir_orden_kfc(self, order_data):
        """Función para imprimir órdenes de KFC"""
        try:
            # Crear contenido del ticket
            ticket_content = f"""
{'=' * 40}
            KFC - ORDEN LISTA
{'=' * 40}
Orden: {order_data.get('order_id', 'N/A')}
Fecha: {order_data.get('fecha', 'N/A')}
Cliente: {order_data.get('cliente', 'N/A')}
Telefono: {order_data.get('telefono', 'N/A')}
{'=' * 40}
PRODUCTOS:
"""

            # Agregar productos
            productos = order_data.get('productos', [])
            for producto in productos:
                ticket_content += f"• {producto.get('nombre', '')} x{producto.get('cantidad', 1)}\n"
                if producto.get('observaciones'):
                    ticket_content += f"  Obs: {producto.get('observaciones')}\n"

            ticket_content += f"""
{'=' * 40}
Total: ${order_data.get('total', '0')}
{'=' * 40}
¡GRACIAS POR SU COMPRA!
{'=' * 40}
"""

            # Imprimir en la impresora física
            success = self.impresora_manager.imprimir_ticket(ticket_content)

            if success:
                logger.info(f"✅ Orden {order_data.get('order_id')} impresa exitosamente")
            else:
                logger.error(f"❌ Error imprimiendo orden {order_data.get('order_id')}")

            return success

        except Exception as e:
            logger.error(f"Error en impresión: {str(e)}")
            return False

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