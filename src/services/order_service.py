import io
import time
import datetime
from typing import Optional, List, Tuple
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from PIL import Image, ImageDraw, ImageFont

from src.database.connection import db_manager
from src.database.queries import *
from src.utils.logger import logger


class OrderService:
    # Configuración de Selenium
    _driver = None

    @staticmethod
    def _setup_driver():
        """Configura el driver de Chrome en modo headless - CORREGIDO CON VERSIÓN COMPATIBLE"""
        try:
            if OrderService._driver:
                try:
                    OrderService._driver.quit()
                except:
                    pass
                OrderService._driver = None

            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--remote-debugging-port=9222")
            chrome_options.add_argument(
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

            # SOLUCIÓN: Forzar la versión compatible de ChromeDriver
            try:
                # Opción 1: Usar la versión más reciente compatible
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
            except Exception as driver_error:
                logger.warning(f"Error con ChromeDriver automático: {driver_error}")
                # Opción 2: Intentar con driver existente en el sistema
                try:
                    driver = webdriver.Chrome(options=chrome_options)
                except Exception as fallback_error:
                    logger.error(f"Error con ChromeDriver fallback: {fallback_error}")
                    # Opción 3: Usar el binary path directo
                    chrome_options.binary_location = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
                    driver = webdriver.Chrome(options=chrome_options)

            # Configurar timeout
            driver.set_page_load_timeout(30)
            driver.implicitly_wait(10)

            OrderService._driver = driver
            logger.info("✅ Driver de Selenium configurado exitosamente")
            return driver

        except Exception as e:
            logger.error(f"❌ Error configurando Chrome driver: {str(e)}")
            OrderService._driver = None
            raise

    @staticmethod
    def validate_store_code(store_code: str) -> bool:
        """Validate store code is within range"""
        return store_code.startswith('K') and len(store_code) >= 4

    @staticmethod
    def _get_store_ip(store_code: str) -> str:
        """Get proper IP address for store"""
        store_number = ''.join(filter(str.isdigit, store_code))
        store_number_int = int(store_number) if store_number else 0
        return f'10.101.{store_number_int}.20'

    @staticmethod
    def get_order_status(store_code: str, order_id: str) -> Optional[Tuple]:
        """Get order status with motorized information"""
        try:
            start_time = time.time()

            results = db_manager.execute_query(
                store_code,
                ORDER_STATUS_QUERY,
                (order_id, order_id)
            )

            elapsed = time.time() - start_time
            if elapsed > 2:
                logger.warning(f"Consulta de estado lenta: {elapsed:.2f}s")

            if results:
                logger.info(f"✅ Orden {order_id} encontrada en {store_code} ({elapsed:.2f}s)")
                return results[0]
            else:
                logger.warning(f"⚠️ Orden {order_id} no encontrada en {store_code}")
                return None

        except Exception as e:
            logger.error(f"❌ Error obteniendo estado orden {order_id}: {str(e)}")
            raise

    @staticmethod
    def audit_order(store_code: str, order_id: str) -> List[Tuple]:
        """Audit order with complete history"""
        try:
            start_time = time.time()

            results = db_manager.execute_query(
                store_code,
                ORDER_AUDIT_QUERY,
                (f'%{order_id}%',)
            )

            elapsed = time.time() - start_time
            logger.info(f"Auditoría completada en {elapsed:.2f}s: {len(results)} registros")
            return results

        except Exception as e:
            logger.error(f"Error en auditoría orden {order_id}: {str(e)}")
            raise

    @staticmethod
    def get_associated_code(store_code: str, cfac_id: str) -> Optional[str]:
        """Get associated code for a given invoice ID"""
        try:
            start_time = time.time()

            query = """
            SELECT TOP 1 codigo_app 
            FROM (
                SELECT codigo_app, 1 as priority 
                FROM Cabecera_App WITH(NOLOCK) 
                WHERE cfac_id = ? AND codigo_app IS NOT NULL

                UNION ALL

                SELECT codigo_app, 2 as priority 
                FROM pickup_cabecera_pedidos WITH(NOLOCK) 
                WHERE cfac_id = ? AND codigo_app IS NOT NULL
            ) AS combined
            ORDER BY priority
            """

            results = db_manager.execute_query(
                store_code,
                query,
                (cfac_id, cfac_id)
            )

            elapsed = time.time() - start_time

            if results and results[0][0]:
                logger.info(f"✅ Código asociado encontrado en {elapsed:.2f}s: {results[0][0]}")
                return results[0][0]

            logger.warning(f"⚠️ No se encontró código asociado para {cfac_id} en ninguna tabla")
            return None

        except Exception as e:
            logger.error(f"❌ Error obteniendo código asociado para {cfac_id}: {str(e)}")
            return None

    @staticmethod
    def get_comanda_url(store_code: str, cfac_id: str) -> Optional[str]:
        """Get comanda URL - CORREGIDA CON CONSULTA ADECUADA"""
        try:
            start_time = time.time()

            # Consulta corregida para obtener ODP_ID
            results = db_manager.execute_query(
                store_code,
                "SELECT TOP 1 IDCabeceraordenPedido FROM Cabecera_Factura WHERE cfac_id = ?",
                (cfac_id,)
            )

            elapsed = time.time() - start_time

            if results and results[0][0]:
                odp_id = results[0][0]
                server_ip = OrderService._get_store_ip(store_code)

                # URL corregida para comanda
                url = f"http://{server_ip}:880/PoS/ordenpedido/impresion/imprimir_ordenpedido.php?odp_id={odp_id}&tipoServicio=2&canalImpresion=0&guardaOrden=0&numeroCuenta=1"

                logger.info(f"✅ URL comanda generada en {elapsed:.2f}s: {url}")
                return url

            logger.warning(f"⚠️ No se encontró comanda para {cfac_id}")
            return None

        except Exception as e:
            logger.error(f"Error obteniendo comanda {cfac_id}: {str(e)}")
            raise

    @staticmethod
    def generate_invoice_image(store_code: str, cfac_id: str) -> io.BytesIO:
        """Genera imagen de factura usando Selenium - SIN MENSAJES TÉCNICOS AL USUARIO"""
        driver = None
        try:
            logger.info(f"🔄 Generando imagen para factura {cfac_id} en tienda {store_code}")

            # Configurar driver
            driver = OrderService._setup_driver()

            # Generar URL CORREGIDA
            server_ip = OrderService._get_store_ip(store_code)
            invoice_url = f"http://{server_ip}:880/pos/facturacion/impresion/impresion_factura.php?cfac_id={cfac_id}&tipo_comprobante=F&"

            logger.info(f"🔗 Navegando a factura: {invoice_url}")

            # Cargar la página
            driver.get(invoice_url)

            # Esperar a que la página cargue completamente
            WebDriverWait(driver, 25).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Dar tiempo extra para que se renderice el contenido
            time.sleep(3)

            # Ajustar tamaño de ventana
            total_height = driver.execute_script(
                "return Math.max(document.body.scrollHeight, document.body.offsetHeight, document.documentElement.clientHeight, document.documentElement.scrollHeight, document.documentElement.offsetHeight);")
            driver.set_window_size(1200, total_height)

            # Tomar screenshot
            screenshot = driver.get_screenshot_as_png()

            # Convertir a BytesIO
            image_buffer = io.BytesIO(screenshot)
            image_buffer.seek(0)

            logger.info(f"✅ Imagen de factura {cfac_id} generada exitosamente")
            return image_buffer

        except Exception as e:
            # NO MOSTRAR DETALLES TÉCNICOS AL USUARIO - solo log interno
            error_msg = "Error al generar imagen"  # Mensaje genérico para el usuario
            logger.error(f"❌ Error en Selenium para factura {cfac_id}: {str(e)}")

            # Generar imagen de error sin detalles técnicos
            return OrderService._generate_error_image(
                store_code,
                cfac_id,
                error_msg,
                OrderService.get_invoice_url(store_code, cfac_id)
            )

        finally:
            # Limpiar recursos silenciosamente
            try:
                if driver:
                    driver.quit()
            except:
                pass

    @staticmethod
    def generate_comanda_image(store_code: str, cfac_id: str) -> io.BytesIO:
        """Genera imagen de comanda usando Selenium - SIN MENSAJES TÉCNICOS"""
        driver = None
        try:
            logger.info(f"🔄 Generando imagen para comanda {cfac_id} en tienda {store_code}")

            # Obtener URL de comanda
            comanda_url = OrderService.get_comanda_url(store_code, cfac_id)
            if not comanda_url:
                raise Exception("No se pudo obtener URL de comanda")

            # Configurar driver
            driver = OrderService._setup_driver()

            logger.info(f"🔗 Navegando a comanda: {comanda_url}")

            # Cargar la página
            driver.get(comanda_url)

            # Esperar a que la página cargue
            WebDriverWait(driver, 25).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Dar tiempo para renderizado
            time.sleep(3)

            # Ajustar tamaño para comanda
            total_height = driver.execute_script(
                "return Math.max(document.body.scrollHeight, document.body.offsetHeight, document.documentElement.clientHeight, document.documentElement.scrollHeight, document.documentElement.offsetHeight);")
            driver.set_window_size(800, total_height)

            # Tomar screenshot
            screenshot = driver.get_screenshot_as_png()
            image_buffer = io.BytesIO(screenshot)
            image_buffer.seek(0)

            logger.info(f"✅ Comanda {cfac_id} generada exitosamente")
            return image_buffer

        except Exception as e:
            # NO MOSTRAR DETALLES TÉCNICOS
            error_msg = "Error al generar comanda"
            logger.error(f"❌ Error en Selenium para comanda {cfac_id}: {str(e)}")

            comanda_url = OrderService.get_comanda_url(store_code, cfac_id)
            return OrderService._generate_error_image(
                store_code,
                cfac_id,
                error_msg,
                comanda_url
            )

        finally:
            # Limpiar recursos silenciosamente
            try:
                if driver:
                    driver.quit()
            except:
                pass

    @staticmethod
    def _generate_error_image(store_code: str, cfac_id: str, error_msg: str, url: str = None) -> io.BytesIO:
        """Genera una imagen de error cuando falla la captura - SIN DETALLES TÉCNICOS"""
        try:
            # Crear imagen
            width, height = 800, 500
            img = Image.new('RGB', (width, height), color='white')
            draw = ImageDraw.Draw(img)

            # Configurar fuentes
            try:
                title_font = ImageFont.truetype("arial.ttf", 28)
                text_font = ImageFont.truetype("arial.ttf", 18)
                url_font = ImageFont.truetype("arial.ttf", 14)
            except:
                title_font = ImageFont.load_default()
                text_font = ImageFont.load_default()
                url_font = ImageFont.load_default()

            # Título
            draw.text((width // 2, 60), "⚠️ Error Generando Imagen", fill='red', font=title_font, anchor='mm')

            # Información de la transacción (sin detalles técnicos)
            info_text = f"🏪 Tienda: {store_code}\n🔢 Documento: {cfac_id}\n❌ Error: {error_msg}"
            draw.text((50, 140), info_text, fill='black', font=text_font)

            # URL alternativa si está disponible
            if url:
                draw.text((50, 260), "🔗 Acceda directamente:", fill='blue', font=text_font)

                # Dividir URL si es muy larga
                max_chars = 70
                if len(url) > max_chars:
                    url_parts = [url[i:i + max_chars] for i in range(0, len(url), max_chars)]
                    for i, part in enumerate(url_parts):
                        draw.text((50, 300 + i * 25), part, fill='blue', font=url_font)
                else:
                    draw.text((50, 300), url, fill='blue', font=url_font)

            # Pie de página
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            draw.text((width // 2, height - 30), f"Generado: {timestamp}", fill='gray', font=url_font, anchor='mm')

            # Convertir a BytesIO
            buf = io.BytesIO()
            img.save(buf, format='PNG', quality=95)
            buf.seek(0)

            logger.info("✅ Imagen de error generada como fallback")
            return buf

        except Exception as e:
            logger.error(f"Error creando imagen de error: {str(e)}")
            return io.BytesIO()

    @staticmethod
    def get_invoice_url(store_code: str, cfac_id: str) -> str:
        """Obtiene la URL de la factura - CORREGIDA"""
        server_ip = OrderService._get_store_ip(store_code)
        return f"http://{server_ip}:880/pos/facturacion/impresion/impresion_factura.php?cfac_id={cfac_id}&tipo_comprobante=F&"

    @staticmethod
    def get_nota_credito_url(store_code: str, cfac_id: str) -> str:
        """Obtiene la URL de la nota de crédito - NUEVO MÉTODO"""
        server_ip = OrderService._get_store_ip(store_code)
        return f"http://{server_ip}:880/pos/facturacion/impresion/impresion_factura.php?cfac_id={cfac_id}&tipo_comprobante=N&"

    @staticmethod
    def test_store_connection(store_code: str) -> bool:
        """Test store connection quickly"""
        try:
            start_time = time.time()

            with db_manager.get_connection(store_code):
                pass  # Solo probar conexión

            elapsed = time.time() - start_time
            logger.info(f"✅ Conexión testeada a {store_code} en {elapsed:.2f}s")
            return True

        except Exception as e:
            logger.error(f"❌ Falló test conexión a {store_code}: {str(e)}")
            return False

    @staticmethod
    def format_order_status_response(status: Tuple, order_id: str) -> str:
        """Format order status response with visual elements"""
        if len(status) == 6:  # With motorized info
            response = (
                f"📦 *Estado de Orden* 🚚\n\n"
                f"🔢 **Código:** `{status[0]}`\n"
                f"📊 **Estado:** `{status[1]}`\n"
                f"🧾 **Factura ID:** `{status[2]}`\n"
                f"📱 **Medio:** `{status[3]}`\n"
                f"🕐 **Fecha:** `{status[4].strftime('%Y-%m-%d %H:%M:%S')}`\n"
                f"🚚 **Motorizado:** `{status[5]}`\n\n"
                f"✅ *Información actualizada*"
            )
        else:
            response = (
                f"📦 *Estado de Orden* 🚚\n\n"
                f"🔢 **Código:** `{order_id}`\n"
                f"📊 **Estado:** `{status[1]}`\n"
                f"🧾 **Factura ID:** `{status[2]}`\n"
                f"🚚 **Motorizado:** `{status[5] if len(status) > 5 else 'No asignado'}`\n\n"
                f"✅ *Información encontrada*"
            )
        return response

    @staticmethod
    def format_audit_response(audit: List[Tuple], order_id: str) -> str:
        """Format audit response with visual elements"""
        if not audit:
            return (
                f"📊 *Auditoría de Orden* 📋\n\n"
                f"🔢 **Código:** `{order_id}`\n\n"
                f"❌ *No se encontró historial de auditoría*\n\n"
                f"💡 **Posibles causas:**\n"
                f"• La orden es muy reciente\n"
                f"• No hay cambios de estado registrados\n"
                f"• La orden no existe en el sistema"
            )

        detalles = []
        for i, row in enumerate(audit, 1):
            detalle = (
                f"**{i}. {row[1]}**\n"
                f"   🕐 {row[2].strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"   🚚 {row[3]}\n"
            )
            detalles.append(detalle)

        response = (
            f"📊 *Auditoría de Orden* 📋\n\n"
            f"🔢 **Código:** `{order_id}`\n"
            f"📈 **Total de registros:** `{len(audit)}`\n\n"
            f"🔄 **Historial de estados:**\n"
            f"{''.join(detalles)}\n"
            f"✅ *Auditoría completada*"
        )
        return response

    @staticmethod
    def get_db_connection(store_code: str):
        """Obtiene conexión a la base de datos"""
        return db_manager.get_connection(store_code)

    @staticmethod
    def cleanup():
        """Limpia los recursos de Selenium"""
        try:
            if OrderService._driver:
                OrderService._driver.quit()
                OrderService._driver = None
                logger.info("✅ Driver de Selenium cerrado correctamente")
        except Exception as e:
            logger.error(f"Error limpiando recursos Selenium: {str(e)}")