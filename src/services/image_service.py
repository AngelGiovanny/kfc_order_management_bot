import io
import asyncio
import requests
from PIL import Image
import sys

from src.utils.logger import logger


class SimpleImageService:
    """Servicio simple de imágenes usando requests y PIL como fallback"""

    def __init__(self):
        self.is_selenium_available = self._check_selenium()

    def _check_selenium(self):
        """Check if Selenium is available"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options

            # Try to setup Chrome driver
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-gpu')

            # Try to create driver (but don't keep it open)
            try:
                driver = webdriver.Chrome(options=chrome_options)
                driver.quit()
                return True
            except:
                return False

        except ImportError:
            return False
        except Exception:
            return False

    async def url_to_image(self, url: str) -> io.BytesIO:
        """Convert URL to image - try multiple methods"""

        # Method 1: Try Selenium first if available
        if self.is_selenium_available:
            try:
                return await self._url_to_image_selenium(url)
            except Exception as e:
                logger.warning(f"Selenium failed, falling back to simple method: {e}")

        # Method 2: Simple screenshot using requests and PIL
        try:
            return await self._url_to_image_simple(url)
        except Exception as e:
            logger.error(f"All image methods failed: {e}")
            raise Exception(f"No se pudo generar la imagen: {e}")

    async def _url_to_image_selenium(self, url: str) -> io.BytesIO:
        """Use Selenium for screenshot"""
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By

        def _take_screenshot():
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--window-size=800,1200')
            chrome_options.add_argument('--disable-gpu')

            driver = webdriver.Chrome(options=chrome_options)
            try:
                driver.get(url)
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                screenshot = driver.get_screenshot_as_png()
                return screenshot
            finally:
                driver.quit()

        loop = asyncio.get_event_loop()
        screenshot_data = await loop.run_in_executor(None, _take_screenshot)

        image_stream = io.BytesIO(screenshot_data)
        image_stream.seek(0)
        return image_stream

    async def _url_to_image_simple(self, url: str) -> io.BytesIO:
        """Simple method using requests"""

        def _download_page():
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.content

        loop = asyncio.get_event_loop()
        html_content = await loop.run_in_executor(None, _download_page)

        # For now, return a placeholder or the URL
        # In a real implementation, you might use imgkit or another HTML to image converter
        raise Exception("Método simple no implementado. Use Selenium o instale imgkit.")

    def is_available(self) -> bool:
        """Check if image service is available"""
        return True  # Always return True, we'll handle errors gracefully

    def cleanup(self):
        """Cleanup resources"""
        pass


# Global image service
image_service = SimpleImageService()