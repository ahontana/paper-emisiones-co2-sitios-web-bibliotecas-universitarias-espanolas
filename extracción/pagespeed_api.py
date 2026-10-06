"""
pagespeed_scraper.py
--------------------
Automatiza el análisis de rendimiento web de un conjunto de URLs universitarias
utilizando la API de Google PageSpeed Insights (Lighthouse v5).

Para cada URL y estrategia (mobile/desktop):

  - Llama a la API de PageSpeed con las categorías: performance, accessibility,
    best-practices y seo.
  - Extrae los scores de cada categoría (0-100).
  - Extrae las métricas Core Web Vitals: LCP, CLS, FCP y TTFB.
  - Extrae el peso total de la página (suma de recursos descargados) en MB o GB.
  - Persiste los resultados de forma incremental en un CSV.
  - Al finalizar, exporta todos los resultados a un archivo Excel.

Dependencias: requests, openpyxl
"""

import csv
import time
import requests
from datetime import datetime
from openpyxl import Workbook


# ---------------------------------------------------------------------------
# CONSTANTES DE CONFIGURACIÓN
# ---------------------------------------------------------------------------

# Clave de API de Google PageSpeed Insights.
# Obtener en: https://developers.google.com/speed/docs/insights/v5/get-started
API_KEY = "INTRODUCE TU CLAVE API"

# Endpoint de la API de PageSpeed Insights v5.
API_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

# Nombre del archivo CSV de progreso incremental.
CSV_PATH = "pagespeed_results.csv"

# Nombre del archivo Excel de salida final.
XLSX_PATH = "pagespeed_results.xlsx"

# Pausa en segundos entre llamadas a la API para evitar errores de cuota.
REQUEST_DELAY_SECONDS = 2

# Cabeceras del CSV de resultados.
CSV_HEADERS = [
    "timestamp",
    "strategy",
    "url",
    "performance_score",
    "accessibility_score",
    "best_practices_score",
    "seo_score",
    "lcp_ms",
    "cls",
    "fcp_ms",
    "ttfb_ms",
    "page_weight_bytes",
    "page_weight_human",
    "status",
    "error",
]


# ---------------------------------------------------------------------------
# FUNCIONES DE PARSEO DE DATOS
# ---------------------------------------------------------------------------

def score_0_100(value):
    """
    Convierte el score de Lighthouse (rango 0.0-1.0) a un entero en escala 0-100.

    La API devuelve los scores como decimales (p.ej. 0.87); esta función los
    normaliza al formato más legible y habitual de 0 a 100.

    Retorna None si el valor no es numérico.
    """
    return round(value * 100) if isinstance(value, (int, float)) else None


def get_audit_numeric(lhr, audit_id):
    """
    Extrae el valor numérico de una auditoría específica del resultado Lighthouse.

    Los valores de auditoría están en la ruta:
        lighthouseResult.audits.<audit_id>.numericValue

    Retorna None si la auditoría no existe o no tiene valor numérico.
    """
    return lhr.get("audits", {}).get(audit_id, {}).get("numericValue")


def get_page_weight(lhr):
    """
    Extrae el peso total de la página (suma de todos los recursos descargados)
    a partir de la auditoría 'total-byte-weight' de Lighthouse.

    Esta auditoría agrega el tamaño en bytes de todos los recursos de red
    (HTML, CSS, JS, imágenes, fuentes, etc.) que el navegador descarga al
    cargar la página.

    Retorna una tupla:
      - page_weight_bytes (int | None): peso total en bytes.
      - page_weight_human (str | None): representación legible en MB o GB,
        con dos decimales (p.ej. '2.43 MB', '1.07 GB').
    """
    total_bytes = get_audit_numeric(lhr, "total-byte-weight")

    if total_bytes is None:
        return None, None

    total_bytes_int = int(total_bytes)

    # Seleccionar unidad según magnitud: GB para páginas >= 1 GB, MB para el resto
    if total_bytes_int >= 1_073_741_824:
        human = f"{total_bytes_int / 1_073_741_824:.2f} GB"
    else:
        human = f"{total_bytes_int / 1_048_576:.2f} MB"

    return total_bytes_int, human


# ---------------------------------------------------------------------------
# LLAMADA A LA API DE PAGESPEED
# ---------------------------------------------------------------------------

def run_pagespeed(url, strategy):
    """
    Ejecuta un análisis de PageSpeed Insights para la URL y estrategia indicadas.

    Parámetros:
      url      -- URL completa del sitio a analizar.
      strategy -- Estrategia de análisis: 'mobile' o 'desktop'.

    Las categorías solicitadas son: performance, accessibility, best-practices y seo.
    El timeout de 90 segundos cubre análisis de páginas lentas sin abortar
    prematuramente la llamada.

    Lanza HTTPError si la API devuelve un código de error HTTP.
    """
    params = {
        "url": url,
        "strategy": strategy,
        "category": [
            "performance",
            "accessibility",
            "best-practices",
            "seo",
        ],
        "key": API_KEY,
    }

    response = requests.get(API_URL, params=params, timeout=90)
    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------------------------
# PARSEO DEL RESULTADO COMPLETO
# ---------------------------------------------------------------------------

def parse_result(data, url, strategy):
    """
    Transforma la respuesta JSON de la API de PageSpeed en una fila de datos
    lista para ser escrita en el CSV.

    Extrae:
      - Scores de categorías Lighthouse (performance, accessibility, best-practices, seo).
      - Métricas Core Web Vitals: LCP, CLS, FCP, TTFB.
      - Peso total de la página en bytes y en formato legible (MB/GB).

    Retorna un diccionario con las claves definidas en CSV_HEADERS.
    """
    lhr = data["lighthouseResult"]
    categories = lhr["categories"]

    page_weight_bytes, page_weight_human = get_page_weight(lhr)

    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "strategy": strategy,
        "url": url,
        "performance_score": score_0_100(categories["performance"]["score"]),
        "accessibility_score": score_0_100(categories["accessibility"]["score"]),
        "best_practices_score": score_0_100(categories["best-practices"]["score"]),
        "seo_score": score_0_100(categories["seo"]["score"]),
        "lcp_ms": get_audit_numeric(lhr, "largest-contentful-paint"),
        "cls": get_audit_numeric(lhr, "cumulative-layout-shift"),
        "fcp_ms": get_audit_numeric(lhr, "first-contentful-paint"),
        "ttfb_ms": get_audit_numeric(lhr, "server-response-time"),
        "page_weight_bytes": page_weight_bytes,
        "page_weight_human": page_weight_human,
        "status": "ok",
        "error": "",
    }


def build_error_row(url, strategy, exc):
    """
    Construye una fila de error para el CSV cuando la llamada a la API
    o el parseo del resultado fallan.

    Todos los campos de métricas se dejan vacíos para facilitar el filtrado
    posterior de filas fallidas.
    """
    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "strategy": strategy,
        "url": url,
        "performance_score": "",
        "accessibility_score": "",
        "best_practices_score": "",
        "seo_score": "",
        "lcp_ms": "",
        "cls": "",
        "fcp_ms": "",
        "ttfb_ms": "",
        "page_weight_bytes": "",
        "page_weight_human": "",
        "status": "fail",
        "error": f"{type(exc).__name__}: {exc}",
    }


# ---------------------------------------------------------------------------
# GESTIÓN DEL CSV INCREMENTAL
# ---------------------------------------------------------------------------

def append_csv(path, row):
    """
    Añade una fila de resultados al CSV de progreso de forma incremental.

    Si el archivo no existe aún, escribe la cabecera antes de la primera fila.
    El flush garantiza la escritura inmediata en disco para proteger el progreso
    ante interrupciones del proceso.
    """
    file_exists = False
    try:
        with open(path, "r", encoding="utf-8"):
            file_exists = True
    except FileNotFoundError:
        pass

    with open(path, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
        f.flush()


# ---------------------------------------------------------------------------
# EXPORTACIÓN A EXCEL
# ---------------------------------------------------------------------------

def csv_to_excel(csv_path, xlsx_path):
    """
    Genera un archivo Excel (.xlsx) a partir del CSV de resultados acumulado.

    La hoja resultante incluye todas las columnas definidas en CSV_HEADERS,
    con una fila de cabecera. Se ejecuta al final del proceso para consolidar
    los resultados en un formato cómodo para revisión y distribución.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "PageSpeed"
    ws.append(CSV_HEADERS)

    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            ws.append([row.get(header, "") for header in CSV_HEADERS])

    wb.save(xlsx_path)
    print(f"[INFO] Excel report generated: {xlsx_path}")


# ---------------------------------------------------------------------------
# PROCESO PRINCIPAL
# ---------------------------------------------------------------------------

def run(urls):
    """
    Punto de entrada principal del proceso de análisis.

    Itera sobre todas las URLs y estrategias (mobile/desktop), llamando a la
    API de PageSpeed para cada combinación. Los resultados se persisten de forma
    incremental en el CSV para permitir reanudar ejecuciones interrumpidas.

    Al finalizar, exporta todos los resultados al archivo Excel de salida.

    Nota: no se implementa aquí un sistema de 'skip URLs ya procesadas' como
    en el scraper de websitecarbon, ya que el objetivo habitual de este script
    es ejecutar un análisis puntual completo. Se puede añadir si fuera necesario.
    """
    for url in urls:
        for strategy in ("mobile", "desktop"):
            print(f"[INFO] Analyzing: {url} [{strategy}]")

            try:
                data = run_pagespeed(url, strategy)
                row = parse_result(data, url, strategy)
                print(
                    f"[INFO] Performance={row['performance_score']} | "
                    f"LCP={row['lcp_ms']} ms | "
                    f"Weight={row['page_weight_human']}"
                )
            except Exception as exc:
                row = build_error_row(url, strategy, exc)
                print(f"[ERROR] Failed: {url} [{strategy}]: {row['error']}")

            append_csv(CSV_PATH, row)

            # Pausa entre llamadas para respetar los límites de cuota de la API
            time.sleep(REQUEST_DELAY_SECONDS)

    csv_to_excel(CSV_PATH, XLSX_PATH)
    print(f"[INFO] Process complete. Results saved to: {CSV_PATH} and {XLSX_PATH}")


# ---------------------------------------------------------------------------
# PUNTO DE ENTRADA
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    urls_to_check = [
        "https://www.uaoceu.es/biblioteca",
        "https://biblioteca.uah.es/",
        #...
    ]

    run(urls_to_check)
