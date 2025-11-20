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