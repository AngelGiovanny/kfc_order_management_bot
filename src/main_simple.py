import logging
from telegram.ext import Application

from src.config.settings import settings
from src.utils.logger import logger
from src.handlers.commands import CommandHandlers
from src.handlers.callbacks import CallbackHandlers
from src.handlers.messages import MessageHandlers


def main():
    """Main function - MEJORADO CON INYECCIÓN DE DEPENDENCIAS"""
    try:
        # Configurar logging
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO
        )

        logger.info("🚀 Iniciando KFC Bot...")
        logger.info("🔧 Verificando configuración...")

        # Verificar token
        if not settings.bot.token:
            logger.error("❌ Token no configurado")
            return

        logger.info("✅ Token configurado correctamente")

        # Crear aplicación
        application = Application.builder().token(settings.bot.token).build()

        logger.info("🔄 Inicializando handlers...")

        # Inicializar handlers con dependencias
        callback_handlers = CallbackHandlers()
        command_handlers = CommandHandlers(callback_handlers)
        message_handlers = MessageHandlers(callback_handlers)

        logger.info("📝 Registrando handlers de comandos...")
        # Agregar todos los handlers
        for handler in command_handlers.get_handlers():
            application.add_handler(handler)

        logger.info("📝 Registrando handlers de callbacks...")
        for handler in callback_handlers.get_handlers():
            application.add_handler(handler)

        logger.info("📝 Registrando handlers de mensajes...")
        for handler in message_handlers.get_handlers():
            application.add_handler(handler)

        # Iniciar el bot
        logger.info("🎉 Bot iniciado correctamente. Escuchando mensajes...")
        application.run_polling()

    except Exception as e:
        logger.error(f"❌ Error crítico iniciando el bot: {str(e)}")
        raise


if __name__ == "__main__":
    main()