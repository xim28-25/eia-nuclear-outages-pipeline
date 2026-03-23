"""
Módulo dataConnector — se encarga de conectarse a la API de la EIA,
descargar los datos de salidas nucleares, validarlos, analizarlos
y guardarlos como archivos .parquet para que dataModel los procese.
"""

import os
import sys
import time
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
import pandas as pd

from dataModel import guardar_analisis 

"""
Configuración del logger para registrar cada etapa del pipeline en consola.
level=INFO muestra mensajes informativos, advertencias y errores.
format incluye fecha, nivel y mensaje para facilitar el debugging.
datefmt define el formato de fecha como YYYY-MM-DD HH:MM:SS.
"""
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

"""
PAGE_SIZE define cuántos registros se piden por página a la API (máximo permitido por la EIA).
MAX_REINTENTOS indica cuántas veces se reintenta una petición fallida antes de abortar.
"""
PAGE_SIZE      = 5000
MAX_REINTENTOS = 3

"""
Diccionario con las URLs base de los tres endpoints disponibles en la API de la EIA.
La llave es el nombre corto que se usa en todo el pipeline para identificar el endpoint.
"""
ENDPOINTS = {
    "us-nuclear-outages":        "https://api.eia.gov/v2/nuclear-outages/us-nuclear-outages/data/",
    "facility-nuclear-outages":  "https://api.eia.gov/v2/nuclear-outages/facility-nuclear-outages/data/",
    "generator-nuclear-outages": "https://api.eia.gov/v2/nuclear-outages/generator-nuclear-outages/data/",
}

"""
Diccionario que define qué columnas deben estar presentes y no nulas en cada endpoint.
Se usa en validar_datos para detectar registros incompletos antes de guardarlos.
"""
CAMPOS_REQUERIDOS = {
    "us-nuclear-outages": ["period", "capacity", "outage", "percentOutage"],
    "facility-nuclear-outages":["period", "facility", "facilityName", "capacity", "outage", "percentOutage"],
    "generator-nuclear-outages": ["period", "facility", "facilityName", "generator", "capacity", "outage", "percentOutage"],
}


"""
Clase EIAConector — encapsula toda la lógica de comunicación con la API de la EIA.
Maneja autenticación, reintentos y paginación para aislar esa complejidad
del resto del pipeline. Se instancia una vez por ejecución del pipeline.
"""
class EIAConector:

    """
    Constructor — recibe la API key como parámetro opcional.
    Si no se pasa, la busca en la variable de entorno EIA_API_KEY.
    Lanza ValueError si no la encuentra para fallar rápido y con mensaje claro.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("EIA_API_KEY")
        if not self.api_key:
            raise ValueError("** Error: EIA_API_KEY no configurada en las variables de entorno")
        logger.info("** API key encontrada correctamente **")

    """
    Método hacer_peticion — ejecuta una petición GET a la URL indicada con los parámetros dados.
    Implementa reintentos con backoff lineal (espera 2s, 4s, 6s) para errores de red.
    Distingue errores de autenticación (401/403) de errores de red para no reintentar
    cuando el problema es la API key, ya que reintentar no lo resolvería.
    Regresa el JSON de respuesta como diccionario o lanza excepción si se agotan los intentos.
    """
    def hacer_peticion(self, url: str, params: dict) -> dict:
        for intento in range(1, MAX_REINTENTOS + 1):
            try:
                logger.info(f"Petición a la API (intento {intento}/{MAX_REINTENTOS})")
                respuesta = requests.get(url, params=params, timeout=30)

                if respuesta.status_code in (401, 403):
                    raise RuntimeError(
                        f"** Error de autenticación (HTTP {respuesta.status_code}). "
                        "** Revisa tu EIA_API_KEY."
                    )

                respuesta.raise_for_status()
                datos = respuesta.json()
                logger.info("** Petición exitosa **")
                return datos

            except RuntimeError:
                raise
            except (requests.ConnectionError, requests.Timeout) as error:
                espera = 2 * intento
                logger.warning(f"** Error de red: {error}. Reintentando en {espera}s")
                time.sleep(espera)

        raise ConnectionError(f"** No se pudo conectar después de {MAX_REINTENTOS} intentos.")

    """
    Método descargar_datos — descarga todos los registros de un endpoint usando paginación.
    Construye los parámetros base de la petición (frecuencia diaria, ordenado por period ASC)
    y agrega filtros de fecha si se proporcionan.
    Itera página por página incrementando el offset en PAGE_SIZE hasta que la API
    devuelva una página vacía o se hayan descargado todos los registros reportados en 'total'.
    Regresa una lista con todos los registros acumulados de todas las páginas.
    """
    def descargar_datos(self, endpoint: str, fecha_inicio: str = None, fecha_fin: str = None) -> list:
        url = ENDPOINTS[endpoint]
        params = {
            "api_key": self.api_key,
            "frequency": "daily",
            "data[0]": "capacity",
            "data[1]": "outage",
            "data[2]": "percentOutage",
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "length": PAGE_SIZE,
            "offset": 0,
        }

        if fecha_inicio:
            params["start"] = fecha_inicio
        if fecha_fin:
            params["end"] = fecha_fin

        todos_los_registros = []
        pagina = 0

        while True:
            pagina += 1
            logger.info(f"** Descargando página {pagina} (offset={params['offset']})")

            cuerpo          = self.hacer_peticion(url, params)
            datos_respuesta = cuerpo.get("response", {})
            registros       = datos_respuesta.get("data", [])
            total           = datos_respuesta.get("total", 0)

            if not registros:
                logger.info(f"Página {pagina} vacía, descarga completada")
                break

            todos_los_registros.extend(registros)
            logger.info(f"Página {pagina}: {len(registros)} registros | Acumulado: {len(todos_los_registros)}/{total or '?'}")

            descargado = params["offset"] + len(registros)
            if (total and descargado >= int(total)) or len(registros) < PAGE_SIZE:
                logger.info("** Todos los registros descargados **")
                break

            params["offset"] += PAGE_SIZE

        logger.info(f"** Total descargado: {len(todos_los_registros)} registros **")
        return todos_los_registros

    """
    Método validar_datos — verifica que los registros descargados tengan las columnas
    requeridas para el endpoint dado, según el diccionario CAMPOS_REQUERIDOS.
    Si falta alguna columna la agrega con valor None para no romper el DataFrame.
    Separa los registros en dos grupos: válidos (sin nulos en campos requeridos)
    e inválidos (con al menos un nulo), y convierte los tipos de las columnas numéricas
    y de fecha en el grupo válido para garantizar consistencia al guardar en parquet.
    Regresa una tupla (df_validos, df_invalidos).
    """
    def validar_datos(self, registros: list, endpoint: str) -> tuple:
        if not registros:
            logger.info("** No hay registros para validar")
            return pd.DataFrame(), pd.DataFrame()

        df     = pd.DataFrame(registros)
        campos = CAMPOS_REQUERIDOS[endpoint]

        for campo in campos:
            if campo not in df.columns:
                logger.warning(f"** Columna faltante: {campo}")
                df[campo] = None

        filas_validas = df[campos].notna().all(axis=1)
        df_validos = df[filas_validas].copy()
        df_invalidos = df[~filas_validas].copy()

        logger.info(
            f"** Validación [{endpoint}]:{len(df_validos)} válidos | {len(df_invalidos)}inválidos"
        )

        if not df_validos.empty:
            df_validos["period"] = pd.to_datetime(df_validos["period"], errors="coerce")
            df_validos["capacity"] = pd.to_numeric(df_validos["capacity"], errors="coerce")
            df_validos["outage"] = pd.to_numeric(df_validos["outage"], errors="coerce")
            df_validos["percentOutage"] = pd.to_numeric(df_validos["percentOutage"], errors="coerce")

        return df_validos, df_invalidos


"""
Función guardar_datos — persiste un DataFrame como archivo .parquet en la ruta indicada.
Intenta primero con pyarrow y luego con fastparquet; si ninguno está disponible
cae a CSV como último recurso y lanza un warning para que se instale pyarrow.
Crea los directorios intermedios si no existen con mkdir(parents=True).
"""
def guardar_datos(df: pd.DataFrame, ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)

    for motor in ("pyarrow", "fastparquet"):
        try:
            df.to_parquet(ruta, engine=motor, index=False)
            logger.info(f"** Guardado en Parquet ({motor}): {ruta.name} **")
            return
        except ImportError:
            logger.debug(f"** Motor {motor} no disponible")

    ruta_csv = ruta.with_suffix(".csv")
    df.to_csv(ruta_csv, index=False)
    logger.warning(
        f"** Sin motor Parquet - guardado como CSV: {ruta_csv} "
        "(instala pyarrow con: pip install pyarrow)"
    )


"""
Función extraer_units — lee las columnas de unidades de medida del DataFrame
(capacity-units, outage-units, percentOutage-units) y construye un DataFrame
de una sola fila para poblar la tabla 'units' en la base de datos.
"""
def extraer_units(df: pd.DataFrame) -> pd.DataFrame:
    units = {
        "capacity_units":       df["capacity-units"].iloc[0],
        "outage_units":         df["outage-units"].iloc[0],
        "percentOutage_units":  df["percentOutage-units"].iloc[0],
    }
    return pd.DataFrame([units])


"""
Función analizar_datos — genera métricas resumen según el endpoint procesado.
Para us-nuclear-outages calcula la tendencia mensual promedio de percentOutage.
Para facility y generator calcula el top 10 de plantas con mayor outage histórico
acumulado en MW y el promedio de percentOutage por planta.
Regresa un diccionario con todas las métricas para ser guardado en la tabla analytics.
"""
def analizar_datos(df: pd.DataFrame, endpoint: str) -> dict:
    if df.empty:
        logger.warning("** No hay datos para analizar")
        return {}

    logger.info(f"** Analizando datos [{endpoint}] **")

    analisis = {
        "endpoint":         endpoint,
        "periodo_inicio":   str(df["period"].min()),
        "periodo_fin":      str(df["period"].max()),
        "total_registros":  len(df),
    }

    """
    Tendencia mensual — agrupa por mes y promedia percentOutage a nivel nacional.
    Solo aplica al endpoint us-nuclear-outages porque es el único con datos agregados.
    """
    if endpoint == "us-nuclear-outages":
        tendencia = (
            df.set_index("period")
            .resample("ME")["percentOutage"]
            .mean()
            .round(2)
            .reset_index()
        )
        tendencia["period"] = tendencia["period"].dt.strftime("%Y-%m")
        analisis["tendencia_mensual"] = tendencia.set_index("period")["percentOutage"].to_dict()
        logger.info(f"** Tendencia mensual calculada ({len(tendencia)} meses) **")

    """
    Análisis por planta — suma el outage total histórico por facilityName para el top 10
    y calcula el promedio de percentOutage por planta para identificar las más afectadas.
    Aplica a facility y generator porque ambos tienen la columna facilityName.
    """
    if "facilityName" in df.columns:
        top10 = (
            df.groupby("facilityName")["outage"]
            .sum()
            .round(2)
            .sort_values(ascending=False)
            .head(10)
            .to_dict()
        )
        promedio_por_planta = (
            df.groupby("facilityName")["percentOutage"]
            .mean()
            .round(2)
            .sort_values(ascending=False)
            .to_dict()
        )
        analisis["top10_plantas_mayor_outage_historico_MW"] = top10
        analisis["promedio_percentOutage_por_planta"] = promedio_por_planta
        logger.info("Top 10 plantas calculado")

    for clave, valor in analisis.items():
        if not isinstance(valor, dict):
            logger.info(f"   {clave}: {valor}")

    return analisis




"""
Función ejecutar — manipula el pipeline completo para un endpoint dado.
Sigue el flujo: descargar - validar - analizar - guardar datos - guardar resumen JSON.
Construye un diccionario 'resumen' que se actualiza en cada etapa para reflejar
el estado final de la ejecución (exitoso, sin_datos, error_autenticacion, fallido).
Los registros inválidos se guardan en un archivo separado para auditoría.
Al final escribe el resumen completo como JSON en la carpeta de salida.
"""
def ejecutar(api_key: str, endpoint: str, carpeta_salida: Path, fecha_inicio: str = None, fecha_fin: str = None) -> dict:

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    logger.info(f"** Iniciando pipeline [{endpoint}] {timestamp} **")

    resumen = {
        "timestamp":           timestamp,
        "endpoint":            endpoint,
        "estado":              "fallido",
        "registros_total":     0,
        "registros_validos":   0,
        "registros_invalidos": 0,
        "archivo_salida":      None,
    }

    conector = EIAConector(api_key)

    """
    DESCARGA
    Si la autenticación falla se detiene aquí con estado 'error_autenticacion'.
    Cualquier otro error de red deja el estado en 'fallido'.
    """
    try:
        registros = conector.descargar_datos(endpoint, fecha_inicio, fecha_fin)
    except RuntimeError as e:
        logger.error(f"** Error de autenticación: {e}")
        resumen["estado"] = "error_autenticacion"
        return resumen
    except Exception as e:
        logger.error(f"** Error en la descarga: {e}")
        return resumen

    resumen["registros_total"] = len(registros)

    if not registros:
        logger.warning("** La API no devolvió datos")
        resumen["estado"] = "sin_datos"
        return resumen

    """
    VALIDACIÓN
    Separa registros válidos e inválidos y actualiza el resumen con los conteos.
    """
    df_validos, df_invalidos = conector.validar_datos(registros, endpoint)
    resumen["registros_validos"]   = len(df_validos)
    resumen["registros_invalidos"] = len(df_invalidos)

    analisis = analizar_datos(df_validos, endpoint)
    resumen["analisis"] = analisis
    guardar_analisis(analisis, Path("nuclear_outages.db"))

    """
    GUARDADO
    Crea la carpeta de salida si no existe, guarda los datos válidos como parquet
    y si hay inválidos los persiste en un archivo separado para revisión posterior.
    """
    carpeta_salida.mkdir(parents=True, exist_ok=True)

    ruta_salida = carpeta_salida / f"nuclear_{endpoint}_{timestamp}.parquet"
    guardar_datos(df_validos, ruta_salida)
    resumen["archivo_salida"] = str(ruta_salida)

    if not df_invalidos.empty:
        ruta_invalidos = carpeta_salida / f"nuclear_{endpoint}_invalidos_{timestamp}.parquet"
        guardar_datos(df_invalidos, ruta_invalidos)

    try:
        df_units   = extraer_units(df_validos)
        ruta_units = carpeta_salida / "units.parquet"
        guardar_datos(df_units, ruta_units)
        logger.info("** Tabla units guardada **")
    except KeyError:
        logger.warning("** No se encontraron columnas de unidades en los datos")

    """
    RESUMEN JSON
    Marca el estado como exitoso y serializa el resumen completo en disco
    para que quede evidencia de cada ejecución del pipeline.
    """
    resumen["estado"] = "exitoso"

    ruta_resumen = carpeta_salida / f"resumen_{timestamp}.json"
    with open(ruta_resumen, "w", encoding="utf-8") as f:
        json.dump(resumen, f, indent=2, default=str)

    logger.info(f"** Pipeline finalizado: {resumen['estado']} ** ")
    return resumen


"""
Punto de entrada — itera sobre los tres endpoints definidos en ENDPOINTS
y ejecuta el pipeline completo para cada uno de forma secuencial.
La API key se toma de la variable de entorno EIA_API_KEY.
fecha_inicio y fecha_fin en None descarga el historial completo disponible.
"""
if __name__ == "__main__":
    resumenes = []

    for endpoint in ENDPOINTS:
        resumen = ejecutar(
            api_key        = os.getenv("EIA_API_KEY"),
            endpoint       = endpoint,
            carpeta_salida = Path("data"),
            fecha_inicio   = None,
            fecha_fin      = None,
        )
        resumenes.append(resumen)