"""
websitecarbon_scraper.py
------------------------
Automatiza el análisis de huella de carbono de un conjunto de URLs introducidas, utilizando el servicio websitecarbon.com. 

Para cada URL:

  - Navega hacia websitecarbon.com mediante Selenium.
  - Introduce una URL de la lista y espera a que se completen los resultados.
  - Extrae los valores de CO2 (gramos), litros de agua y energía desde el diccionario embedido en el header, que se corresponde con los valores que muestra en el body.
    <script type="text/javascript">
        var stat_values = {
            "grams": 0.086283597587608,
            "litres": 0.047990936978227,
            "energy": 0.00017466315301135,
            "monthly_views": 10000,
        };
    </script>
  - Desde el body, se extrae el tipo de energía (sostenible o estándar) y la calificación.
  - Guarda el HTML de la página de resultados como archivo local para auditoría posterior.
  - Persiste los resultados de forma incremental en un CSV, lo que permite reanudar ejecuciones. Especialmente interesante si una ejecución se corta a mitad
  - Al finalizar, exporta todos los resultados a un archivo Excel.

Dependencias: selenium, beautifulsoup4, openpyxl
"""

# ---------------------------------------------------------------------------
# LIBRERÍAS
# ---------------------------------------------------------------------------

import time
import re
import ast
import csv
import os
from datetime import datetime
from urllib.parse import urlparse

from openpyxl import Workbook

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
)

from bs4 import BeautifulSoup, Comment


# ---------------------------------------------------------------------------
# CONSTANTES DE CONFIGURACIÓN
# ---------------------------------------------------------------------------

# Nombre del archivo CSV de progreso (permite reanudar la ejecución).
PROGRESS_CSV_PATH = "resultados_progreso.csv"

# Nombre del archivo Excel de salida final.
OUTPUT_XLSX_PATH = "resultados.xlsx"

# Directorio donde se guardarán los archivos HTML de los análisis.
HTML_OUTPUT_DIR = "html_results"

# Cabeceras del CSV de progreso.
CSV_HEADERS = [
    "url",
    "co2_grams",
    "litres",
    "energy",
    "energy_type",
    "grade",
    "status",
    "error",
    "timestamp",
    "html_file",
]

# Excepciones de Selenium que se consideran transitorias y permiten reintento.
RETRYABLE_EXCEPTIONS = (
    TimeoutException,
    WebDriverException,
    StaleElementReferenceException,
)


# ---------------------------------------------------------------------------
# EXTRACCIÓN DE DATOS DESDE EL HTML
# ---------------------------------------------------------------------------

def extract_energy_type(soup: BeautifulSoup) -> str | None:
    """
    Determina el tipo de energía del servidor analizado.

    Elimina primero los comentarios HTML para evitar falsos positivos,
    y luego busca las cadenas identificativas en el texto visible.

    Retorna 'bog standard energy', 'sustainable energy', o None si no se encuentra.
    """
    # Eliminar comentarios HTML antes de analizar el texto
    for comment in soup(text=lambda text: isinstance(text, Comment)):
        comment.extract()

    text = soup.get_text(separator=" ").lower()

    if "bog standard energy" in text:
        return "bog standard energy"
    elif "sustainable energy" in text:
        return "sustainable energy"

    return None

def extract_stat_values(soup: BeautifulSoup) -> tuple[float | None, float | None, float | None]:
    """
    Extrae los valores estadísticos principales desde el objeto JS 'stat_values'
    embebido en la página de resultados.

    websitecarbon.com inyecta los datos de análisis en un bloque <script> con la forma:
        var stat_values = { "grams": ..., "litres": ..., "energy": ... }; Por ejemplo:

            <script type="text/javascript">
                var stat_values = {
                    "grams": 0.086283597587608,
                    "litres": 0.047990936978227,
                    "energy": 0.00017466315301135,
                    "monthly_views": 10000,
                };
            </script>

    Retorna una tupla (grams, litres, energy). Cualquier valor puede ser None
    si el bloque JS no se encuentra o no se puede parsear.
    """
    script = soup.find("script", string=re.compile(r"var stat_values"))
    if not script or not script.string:
        return None, None, None

    match = re.search(r"var stat_values\s*=\s*({.*?});", script.string, re.DOTALL)
    if not match:
        return None, None, None

    try:
        stat_values = ast.literal_eval(match.group(1))
        return (
            stat_values.get("grams"),
            stat_values.get("litres"),
            stat_values.get("energy"),
        )
    except (ValueError, SyntaxError):
        return None, None, None

def extract_grade(soup: BeautifulSoup) -> str | None:
    """
    Extrae la calificación de carbono (A+, A, B, C, D, E, F) del bloque de
    resumen del informe.

    El texto tiene la forma: "This web page achieves a carbon rating of B"
    """
    rating_div = soup.find("div", class_="report-summary__heading retest")
    if not rating_div:
        return None

    raw = rating_div.get_text()
    parts = raw.split("This web page achieves a carbon rating of")
    if len(parts) < 2:
        return None

    return parts[-1].strip()


# ---------------------------------------------------------------------------
# GESTIÓN DEL HTML DE RESULTADOS
# ---------------------------------------------------------------------------

def build_html_filename(url: str, prefix: str = "") -> str:
    """
    Construye un nombre de archivo HTML a partir del dominio de la URL analizada.

    Ejemplo: 'https://biblioteca.ucm.es/' -> 'biblioteca_ucm_es.html'
    Se aplica un prefijo opcional (p.ej. 'ERROR_') para archivos de depuración.
    """
    domain = urlparse(url).netloc.replace("www.", "").replace(".", "_")
    domain = domain or "unknown_domain"
    return f"{prefix}{domain}.html"


def save_html(html_content: str, filename: str, output_dir: str) -> str:
    """
    Guarda el contenido HTML en el directorio de salida especificado.

    Crea el directorio si no existe. Devuelve la ruta completa del archivo guardado.
    """
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)

    return filepath


# ---------------------------------------------------------------------------
# GESTIÓN DEL PROGRESO (CSV INCREMENTAL)
# ---------------------------------------------------------------------------

def load_done_urls(csv_path: str) -> set:
    """
    Lee el CSV de progreso y devuelve el conjunto de URLs ya procesadas,
    tanto las exitosas como las fallidas.

    Esto permite reanudar la ejecución sin reprocesar URLs ya registradas.
    """
    done = set()
    if not os.path.exists(csv_path):
        return done

    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get("url", "").strip()
            if url:
                done.add(url)

    return done


def append_result(csv_path: str, row: dict) -> None:
    """
    Añade una fila de resultados al CSV de progreso.

    Si el archivo no existe, escribe la cabecera antes de la primera fila.
    Usa flush() para garantizar escritura inmediata en disco incluso ante
    interrupciones del proceso.
    """
    file_exists = os.path.exists(csv_path)

    with open(csv_path, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
        f.flush()


# ---------------------------------------------------------------------------
# UTILIDADES DE SELENIUM
# ---------------------------------------------------------------------------

def safe_click(driver: webdriver.Chrome, element) -> None:
    """
    Realiza un clic robusto sobre un elemento del DOM con tres estrategias
    en orden de preferencia:

    1. Clic directo estándar de Selenium.
    2. Clic mediante ActionChains (útil cuando el elemento está parcialmente
       fuera del viewport o hay overlays).
    3. Clic forzado mediante JavaScript (último recurso).
    """
    try:
        element.click()
        return
    except (ElementClickInterceptedException, WebDriverException):
        pass

    try:
        ActionChains(driver).move_to_element(element).click().perform()
        return
    except WebDriverException:
        pass

    driver.execute_script("arguments[0].click();", element)


def wait_for_results(driver: webdriver.Chrome, timeout_seconds: int = 60) -> None:
    """
    Espera a que la página de websitecarbon.com haya terminado de calcular
    los resultados, detectando la aparición del contador animado (js-countup),
    que solo se renderiza una vez que los datos están disponibles.

    Lanza TimeoutException si el elemento no aparece en el tiempo indicado.
    """
    wait = WebDriverWait(driver, timeout_seconds)
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "js-countup")))


# ---------------------------------------------------------------------------
# ANÁLISIS DE UNA URL
# ---------------------------------------------------------------------------

def test_website(
    url_to_check: str,
    driver: webdriver.Chrome,
    save_html_on_success: bool = True,
    save_html_on_error: bool = True,
    html_output_dir: str = HTML_OUTPUT_DIR,
) -> dict:
    """
    Analiza una URL en websitecarbon.com y extrae todos los datos disponibles.

    Flujo:
      1. Carga la página principal de websitecarbon.com.
      2. Introduce la URL en el formulario y lanza el análisis.
      3. Espera a que los resultados se rendericen.
      4. Guarda el HTML de resultados si se indica (para auditoría).
      5. Extrae CO2, litros, energía, tipo de energía y calificación.

    Parámetros:
      url_to_check       -- URL del sitio a analizar.
      driver             -- Instancia activa de Selenium WebDriver.
      save_html_on_success -- Si True, guarda el HTML cuando el análisis es exitoso.
      save_html_on_error   -- Si True, guarda el HTML cuando se produce un error,
                              prefijando el archivo con 'ERROR_' para fácil identificación.
      html_output_dir    -- Directorio de destino para los archivos HTML.

    Retorna un diccionario con los campos definidos en CSV_HEADERS.
    """
    print(f"[INFO] Analyzing: {url_to_check}")

    html_file_path = ""

    try:
        # Navegar al formulario de análisis
        driver.get("https://www.websitecarbon.com/")

        wait = WebDriverWait(driver, 20)
        url_field = wait.until(EC.presence_of_element_located((By.ID, "wgd-cc-url")))
        url_field.clear()
        url_field.send_keys(url_to_check)

        calculate_button = wait.until(EC.element_to_be_clickable((By.ID, "js-new-test-button")))
        safe_click(driver, calculate_button)

        # Esperar a que los resultados se rendericen completamente
        wait_for_results(driver, timeout_seconds=60)

        page_source = driver.page_source

        # Guardar el HTML de resultados para auditoría
        if save_html_on_success:
            filename = build_html_filename(url_to_check)
            html_file_path = save_html(page_source, filename, html_output_dir)
            print(f"[INFO] HTML saved: {html_file_path}")

        # Parsear y extraer datos
        soup = BeautifulSoup(page_source, "html.parser")

        grams, litres, energy = extract_stat_values(soup)
        energy_type = extract_energy_type(soup)
        grade = extract_grade(soup)

        print(
            f"[INFO] CO2={grams}g | Litres={litres} | Energy={energy} "
            f"| Type={energy_type} | Grade={grade}"
        )

        return {
            "url": url_to_check,
            "co2_grams": grams,
            "litres": litres,
            "energy": energy,
            "energy_type": energy_type,
            "grade": grade,
            "status": "ok",
            "error": "",
            "html_file": html_file_path,
        }

    except Exception as exc:
        # Intentar guardar el HTML del estado de error para depuración
        if save_html_on_error:
            try:
                page_source = driver.page_source
                error_filename = build_html_filename(url_to_check, prefix="ERROR_")
                html_file_path = save_html(page_source, error_filename, html_output_dir)
                print(f"[WARNING] Error HTML saved: {html_file_path}")
            except Exception:
                pass

        error_msg = f"{type(exc).__name__}: {exc}"
        print(f"[ERROR] Failed to analyze {url_to_check}: {error_msg}")

        return {
            "url": url_to_check,
            "co2_grams": None,
            "litres": None,
            "energy": None,
            "energy_type": None,
            "grade": None,
            "status": "fail",
            "error": error_msg,
            "html_file": html_file_path,
        }


# ---------------------------------------------------------------------------
# REINTENTOS CON BACKOFF LINEAL
# ---------------------------------------------------------------------------

def test_with_retries(
    url: str,
    driver: webdriver.Chrome,
    max_retries: int = 3,
    base_sleep_seconds: int = 3,
    **kwargs,
) -> dict:
    """
    Ejecuta el análisis de una URL con soporte de reintentos ante fallos.

    Estrategia de backoff: cada reintento espera base_sleep_seconds * intento,
    lo que reduce la presión sobre el servicio externo en caso de errores
    transitorios (timeouts, elementos obsoletos, etc.).

    Siempre devuelve el último resultado obtenido, incluso si todos los
    intentos fallaron.
    """
    last_result = None

    for attempt in range(1, max_retries + 1):
        result = test_website(url, driver, **kwargs)
        last_result = result

        if result["status"] == "ok":
            return result

        wait_seconds = base_sleep_seconds * attempt
        print(f"[WARNING] Attempt {attempt}/{max_retries} failed. Retrying in {wait_seconds}s...")
        time.sleep(wait_seconds)

    return last_result


# ---------------------------------------------------------------------------
# EXPORTACIÓN A EXCEL
# ---------------------------------------------------------------------------

def save_to_excel_from_csv(csv_path: str, xlsx_path: str = OUTPUT_XLSX_PATH) -> None:
    """
    Genera un archivo Excel (.xlsx) a partir del CSV de progreso acumulado.

    La hoja resultante incluye todas las columnas de CSV_HEADERS con una fila
    de cabecera. Se ejecuta al final del proceso para consolidar los resultados
    en un formato cómodo para revisión y distribución.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Resultados"
    ws.append(CSV_HEADERS)

    if os.path.exists(csv_path):
        with open(csv_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ws.append([row.get(header, "") for header in CSV_HEADERS])

    wb.save(xlsx_path)
    print(f"[INFO] Excel report generated: {xlsx_path}")


# ---------------------------------------------------------------------------
# PROCESO PRINCIPAL
# ---------------------------------------------------------------------------

def evaluate_urls() -> None:
    """
    Punto de entrada principal del proceso de evaluación.

    Carga la lista de URLs, descarta las ya procesadas según el CSV de progreso,
    y lanza el análisis secuencial con reintentos para las URLs pendientes.

    Al finalizar, exporta todos los resultados al archivo Excel de salida.
    """
    urls_to_check = [
        "https://www.uaoceu.es/biblioteca",
        "https://biblioteca.uah.es/",
        #...  
    ]

    # Cargar URLs ya procesadas para poder reanudar ejecuciones interrumpidas
    done_urls = load_done_urls(PROGRESS_CSV_PATH)
    pending = [url for url in urls_to_check if url not in done_urls]

    print(
        f"[INFO] Total URLs: {len(urls_to_check)} | "
        f"Already processed: {len(done_urls)} | "
        f"Pending: {len(pending)}"
    )

    # Configurar el driver de Chrome
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Descomentar para modo headless (sin ventana de navegador):
    # options.add_argument("--headless=new")

    driver = webdriver.Chrome(options=options)

    try:
        for idx, url in enumerate(pending, start=1):
            print(f"\n[INFO] --- ({idx}/{len(pending)}) ---")

            result = test_with_retries(
                url,
                driver,
                max_retries=3,
                base_sleep_seconds=3,
                save_html_on_success=True,
                save_html_on_error=True,
                html_output_dir=HTML_OUTPUT_DIR,
            )
            result["timestamp"] = datetime.now().isoformat(timespec="seconds")

            append_result(PROGRESS_CSV_PATH, result)

            # Pausa entre URLs para reducir carga sobre el servicio externo
            print(f"[INFO] Waiting 5s before next URL...")
            time.sleep(5)

    finally:
        # Garantizar el cierre del driver aunque se produzca una excepción
        driver.quit()

    save_to_excel_from_csv(PROGRESS_CSV_PATH, OUTPUT_XLSX_PATH)


# ---------------------------------------------------------------------------
# PUNTO DE ENTRADA
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    evaluate_urls()
